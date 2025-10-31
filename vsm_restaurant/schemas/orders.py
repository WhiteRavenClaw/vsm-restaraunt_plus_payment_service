from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .menu import MenuItemOut
from ..db.orders import PaymentMethod, OrderStatus

class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1

class OrderCreate(BaseModel):
    place_id: str
    payment_method: PaymentMethod
    items: List[OrderItemCreate]

class OrderItemOut(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    menu_item: Optional[MenuItemOut] = None

class OrderOut(BaseModel):
    id: int
    place_id: str
    created_at: datetime
    payment_method: PaymentMethod
    status: OrderStatus
    total_price: float
    payment_link: Optional[str] = None
    items: List[OrderItemOut]