import argparse
import csv
import sqlite3
from collections import Counter
from pathlib import Path

from app.database import get_connection


def parse_customer_id(value: str) -> int:
    return int(float(value))


def load_csv(csv_path: str | Path, db_path: str | Path) -> Counter:
    rejected = Counter()
    db = get_connection(db_path)
    try:
        with Path(csv_path).open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row_number, row in enumerate(reader, start=2):
                try:
                    if not row.get("CustomerID", "").strip():
                        rejected["CustomerID ausente"] += 1
                        continue
                    customer_id = parse_customer_id(row["CustomerID"])
                    unit_price = float(row["UnitPrice"])
                    quantity = int(row["Quantity"])
                except (KeyError, TypeError, ValueError):
                    rejected["formato numérico inválido"] += 1
                    continue
                if unit_price <= 0:
                    rejected["UnitPrice <= 0"] += 1
                    continue
                if quantity == 0:
                    rejected["Quantity = 0"] += 1
                    continue

                try:
                    db.execute("SAVEPOINT fila")
                    db.execute(
                        "INSERT OR IGNORE INTO clientes(customer_id, pais) VALUES (?, ?)",
                        (customer_id, row["Country"].strip()),
                    )
                    db.execute(
                        "INSERT OR IGNORE INTO productos(stock_code, descripcion) VALUES (?, ?)",
                        (row["StockCode"].strip(), row["Description"].strip() or row["StockCode"].strip()),
                    )
                    db.execute(
                        """
                        INSERT OR IGNORE INTO pedidos(invoice_no, customer_id, fecha, es_cancelacion)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            row["InvoiceNo"].strip(),
                            customer_id,
                            row["InvoiceDate"].strip(),
                            int(row["InvoiceNo"].strip().startswith("C")),
                        ),
                    )
                    db.execute(
                        """
                        INSERT INTO lineas_pedido(invoice_no, stock_code, cantidad, precio_unitario)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            row["InvoiceNo"].strip(),
                            row["StockCode"].strip(),
                            quantity,
                            unit_price,
                        ),
                    )
                    db.execute("RELEASE SAVEPOINT fila")
                except sqlite3.IntegrityError as error:
                    db.execute("ROLLBACK TO SAVEPOINT fila")
                    db.execute("RELEASE SAVEPOINT fila")
                    if "UNIQUE constraint failed" in str(error):
                        rejected["duplicado exacto"] += 1
                    else:
                        rejected[f"error de integridad (fila {row_number})"] += 1
        db.commit()
    finally:
        db.close()

    total = sum(rejected.values())
    print(f"Filas rechazadas: {total}")
    for reason, count in rejected.items():
        print(f"- {reason}: {count}")
    return rejected


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga datos_originales.csv en la base E1")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--db-path", type=Path, default=Path("mtr_play_e1.sqlite"))
    args = parser.parse_args()
    load_csv(args.csv_path, args.db_path)


if __name__ == "__main__":
    main()
