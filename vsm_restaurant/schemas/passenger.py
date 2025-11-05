from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..db.orders import OrderStatus, PaymentMethod
from .orders import OrderItemOut

class PassengerOrderStatus(BaseModel):
    """Упрощенный статус заказа для пассажиров"""
    order_id: int
    place_id: str
    status: OrderStatus
    total_price: float
    created_at: datetime
    estimated_time: Optional[str] = None  # Примерное время готовности
    items: List[OrderItemOut]

class OrderStatusResponse(BaseModel):
    success: bool
    order: Optional[PassengerOrderStatus] = None
    message: Optional[str] = None

class PassengerOrderHistory(BaseModel):
    """История заказов пассажира"""
    order_id: int
    status: OrderStatus
    total_price: float
    created_at: datetime
    item_count: int