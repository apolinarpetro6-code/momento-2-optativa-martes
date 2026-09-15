import csv

from pipeline import load_csv


def test_pipeline_rejects_invalid_rows_and_continues(database_path, tmp_path, capsys):
    csv_path = tmp_path / "input.csv"
    rows = [
        ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"],
        ["PIPE-1", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", "1", "2026-09-15 10:00", "2.55", "17850", "United Kingdom"],
        ["PIPE-1", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", "1", "2026-09-15 10:00", "2.55", "17850", "United Kingdom"],
        ["PIPE-2", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", "1", "2026-09-15 10:00", "0", "17850", "United Kingdom"],
        ["PIPE-3", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", "1", "2026-09-15 10:00", "2.55", "", "United Kingdom"],
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        csv.writer(file).writerows(rows)

    rejected = load_csv(csv_path, database_path)
    output = capsys.readouterr().out

    assert rejected["duplicado exacto"] == 1
    assert rejected["UnitPrice <= 0"] == 1
    assert rejected["CustomerID ausente"] == 1
    assert "Filas rechazadas: 3" in output
