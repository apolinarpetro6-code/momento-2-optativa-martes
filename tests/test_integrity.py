import sqlite3

import pytest

from app.database import get_connection


def test_rejects_order_with_unknown_customer(database_path):
    db = get_connection(database_path)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        db.execute(
            "INSERT INTO pedidos(invoice_no, customer_id, fecha, es_cancelacion) "
            "VALUES ('TEST-001', 999999, '2010-12-31 12:00', 0)"
        )
    db.close()


def test_rejects_line_with_zero_price(database_path):
    db = get_connection(database_path)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        db.execute(
            """
            INSERT INTO lineas_pedido(invoice_no, stock_code, cantidad, precio_unitario)
            VALUES (
                (SELECT invoice_no FROM pedidos LIMIT 1),
                (SELECT stock_code FROM productos LIMIT 1),
                1,
                0
            )
            """
        )
    db.close()


def test_rejects_line_with_unknown_product(database_path):
    db = get_connection(database_path)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        db.execute(
            """
            INSERT INTO lineas_pedido(invoice_no, stock_code, cantidad, precio_unitario)
            VALUES (
                (SELECT invoice_no FROM pedidos LIMIT 1),
                'NO-EXISTE-999',
                1,
                5.0
            )
            """
        )
    db.close()
