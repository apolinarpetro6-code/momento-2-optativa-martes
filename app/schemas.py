from typing import Optional

from pydantic import BaseModel


class OrderLineCreate(BaseModel):
    stock_code: str
    cantidad: int
    precio_unitario: float


class OrderCreate(BaseModel):
    invoice_no: str
    customer_id: int
    fecha: Optional[str] = None
    es_cancelacion: int = 0
    lineas: list[OrderLineCreate]
