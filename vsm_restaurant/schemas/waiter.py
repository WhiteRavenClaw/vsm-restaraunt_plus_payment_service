from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..db.orders import OrderStatus, PaymentMethod
from .orders import OrderOut

class WaiterOrderSummary(BaseModel):
    id: int
    place_id: str
    status: OrderStatus
    total_price: float
    payment_method: PaymentMethod
    created_at: datetime
    item_count: int

class DeliveryUpdate(BaseModel):
    status: OrderStatus

class PaymentReceived(BaseModel):
    payment_method: PaymentMethod  # Для подтверждения способа оплаты

