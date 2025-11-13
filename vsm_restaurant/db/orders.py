from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, DateTime

class PaymentMethod(str, Enum):
    CARD_ONLINE = "card_online"
    CARD_TERMINAL = "card_terminal"
    CASH = "cash"
    SBP = "sbp"

class OrderStatus(str, Enum):
    WAITING_PAYMENT = "waiting_payment"
    PAID = "paid"
    COOKING = "cooking"
    PARTIALLY_DELIVERED = "partially_delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    menu_item_id: int = Field(foreign_key="menu.id")
    quantity: int = Field(default=1)
    order: Optional["Order"] = Relationship(back_populates="items")
    menu_item: Optional["MenuItemModel"] = Relationship(back_populates="order_items")
    
    

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    place_id: str = Field()
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    payment_timeout_at: Optional[datetime] = Field(default=None) 
    transaction_id: Optional[str] = Field(default=None)
    payment_method: PaymentMethod = Field(default=PaymentMethod.CARD_ONLINE)
    status: OrderStatus = Field(default=OrderStatus.WAITING_PAYMENT)
    total_price: float = Field(default=0.0)
    payment_link: Optional[str] = Field(default=None)
    items: List[OrderItem] = Relationship(back_populates="order")
    cooking_tasks: List["CookingTask"] = Relationship(back_populates="order")

    
    