from fastapi.testclient import TestClient

from app import main


def test_create_order_is_atomic(database_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", database_path)
    client = TestClient(main.app)
    response = client.post(
        "/pedidos",
        json={
            "invoice_no": "TEST-ATOMIC",
            "customer_id": 17850,
            "fecha": "2026-09-15 10:00",
            "lineas": [
                {"stock_code": "85123A", "cantidad": 1, "precio_unitario": 2.55},
                {"stock_code": "NO-EXISTE-999", "cantidad": 1, "precio_unitario": 5},
            ],
        },
    )
    assert response.status_code == 404

    with main.connection() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM pedidos WHERE invoice_no = 'TEST-ATOMIC'"
        ).fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM lineas_pedido WHERE invoice_no = 'TEST-ATOMIC'"
        ).fetchone()[0] == 0


def test_create_order_rejects_invalid_price(database_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", database_path)
    response = TestClient(main.app).post(
        "/pedidos",
        json={
            "invoice_no": "TEST-PRICE",
            "customer_id": 17850,
            "lineas": [{"stock_code": "85123A", "cantidad": 1, "precio_unitario": 0}],
        },
    )
    assert response.status_code == 400
    assert "mayor que cero" in response.json()["detail"]
