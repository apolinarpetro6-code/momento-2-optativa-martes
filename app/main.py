import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from .database import get_connection
from .schemas import OrderCreate


DB_PATH = Path(__file__).resolve().parent.parent / "mtr_play_e1.sqlite"
app = FastAPI(title="Mtr Play E2 API")


def connection() -> sqlite3.Connection:
    return get_connection(DB_PATH)


def integrity_error_message(error: sqlite3.IntegrityError) -> str:
    return str(error)


@app.post("/pedidos", status_code=201)
def create_order(order: OrderCreate) -> dict:
    if not order.lineas:
        raise HTTPException(status_code=400, detail="El pedido debe tener al menos una línea")
    if order.es_cancelacion not in (0, 1):
        raise HTTPException(status_code=400, detail="es_cancelacion debe ser 0 o 1")
    for line in order.lineas:
        if line.cantidad == 0:
            raise HTTPException(
                status_code=400,
                detail=f"La cantidad de {line.stock_code} no puede ser cero",
            )
        if line.precio_unitario <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"El precio de {line.stock_code} debe ser mayor que cero",
            )

    db = connection()
    try:
        if db.execute(
            "SELECT 1 FROM clientes WHERE customer_id = ?", (order.customer_id,)
        ).fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"El cliente {order.customer_id} no existe "
                    "(SQLite: FOREIGN KEY constraint failed)"
                ),
            )

        missing_products = [
            line.stock_code
            for line in order.lineas
            if db.execute(
                "SELECT 1 FROM productos WHERE stock_code = ?", (line.stock_code,)
            ).fetchone()
            is None
        ]
        if missing_products:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Producto(s) inexistente(s): {', '.join(missing_products)} "
                    "(SQLite: FOREIGN KEY constraint failed)"
                ),
            )

        db.execute("BEGIN")
        db.execute(
            """
            INSERT INTO pedidos(invoice_no, customer_id, fecha, es_cancelacion)
            VALUES (?, ?, ?, ?)
            """,
            (
                order.invoice_no,
                order.customer_id,
                order.fecha or datetime.now(timezone.utc).isoformat(),
                order.es_cancelacion,
            ),
        )
        for line in order.lineas:
            db.execute(
                """
                INSERT INTO lineas_pedido(invoice_no, stock_code, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
                """,
                (
                    order.invoice_no,
                    line.stock_code,
                    line.cantidad,
                    line.precio_unitario,
                ),
            )
        db.commit()
        return {"invoice_no": order.invoice_no, "lineas": len(order.lineas)}
    except HTTPException:
        db.rollback()
        raise
    except sqlite3.IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=integrity_error_message(error)) from error
    finally:
        db.close()


@app.get("/productos/{stock_code}/ventas")
def product_sales(
    stock_code: str,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    db = connection()
    try:
        if db.execute(
            "SELECT 1 FROM productos WHERE stock_code = ?", (stock_code,)
        ).fetchone() is None:
            raise HTTPException(status_code=404, detail=f"El producto {stock_code} no existe")
        rows = db.execute(
            """
            SELECT l.invoice_no, pe.customer_id, pe.fecha, l.cantidad,
                   l.precio_unitario, ROUND(l.cantidad * l.precio_unitario, 2) AS total
            FROM lineas_pedido AS l
            JOIN pedidos AS pe ON pe.invoice_no = l.invoice_no
            WHERE l.stock_code = ?
            ORDER BY pe.fecha DESC, l.invoice_no
            LIMIT ?
            """,
            (stock_code, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


@app.get("/clientes/{customer_id}/pedidos")
def customer_orders(customer_id: int) -> list[dict]:
    db = connection()
    try:
        if db.execute(
            "SELECT 1 FROM clientes WHERE customer_id = ?", (customer_id,)
        ).fetchone() is None:
            raise HTTPException(status_code=404, detail=f"El cliente {customer_id} no existe")
        rows = db.execute(
            """
            SELECT pe.invoice_no, pe.fecha, pe.es_cancelacion,
                   COUNT(l.id) AS lineas,
                   ROUND(COALESCE(SUM(l.cantidad * l.precio_unitario), 0), 2) AS total
            FROM pedidos AS pe
            LEFT JOIN lineas_pedido AS l ON l.invoice_no = pe.invoice_no
            WHERE pe.customer_id = ?
            GROUP BY pe.invoice_no
            ORDER BY pe.fecha DESC, pe.invoice_no
            """,
            (customer_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


@app.get("/reportes/top-productos")
def top_products(limit: int = Query(default=10, ge=1, le=100)) -> list[dict]:
    db = connection()
    try:
        rows = db.execute(
            """
            SELECT p.descripcion, SUM(l.cantidad) AS unidades_vendidas
            FROM lineas_pedido l
            JOIN productos p ON p.stock_code = l.stock_code
            JOIN pedidos pe ON pe.invoice_no = l.invoice_no
            WHERE pe.es_cancelacion = 0
            GROUP BY p.stock_code
            ORDER BY unidades_vendidas DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


@app.get("/reportes/top-clientes")
def top_customers(limit: int = Query(default=10, ge=1, le=100)) -> list[dict]:
    db = connection()
    try:
        rows = db.execute(
            """
            SELECT c.customer_id, c.pais,
                   ROUND(SUM(l.cantidad * l.precio_unitario), 2) AS total_comprado
            FROM lineas_pedido l
            JOIN pedidos pe ON pe.invoice_no = l.invoice_no
            JOIN clientes c ON c.customer_id = pe.customer_id
            WHERE pe.es_cancelacion = 0
            GROUP BY c.customer_id
            ORDER BY total_comprado DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


@app.get("/reportes/ventas-por-pais")
def sales_by_country(limit: int = Query(default=10, ge=1, le=100)) -> list[dict]:
    db = connection()
    try:
        rows = db.execute(
            """
            SELECT c.pais, COUNT(DISTINCT pe.invoice_no) AS pedidos,
                   ROUND(SUM(l.cantidad * l.precio_unitario), 2) AS total
            FROM lineas_pedido l
            JOIN pedidos pe ON pe.invoice_no = l.invoice_no
            JOIN clientes c ON c.customer_id = pe.customer_id
            WHERE pe.es_cancelacion = 0
            GROUP BY c.pais
            ORDER BY total DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()
