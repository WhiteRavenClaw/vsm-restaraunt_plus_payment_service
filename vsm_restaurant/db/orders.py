from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import VARCHAR, INTEGER
from sqlmodel import Field, SQLModel
from sqlmodel import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum



class PaymentMethod(str, Enum):
    CARD_ONLINE = "card_online"
    CARD_TERMINAL = "card_terminal"
    CASH = "cash"

class OrderStatus(str, Enum):
    WAITING_PAYMENT = "waiting_payment"
    PAID = "paid"
    COOKING = "cooking"
    PARTIALLY_DELIVERED = "partially_delivered"
    COMPLETED = "completed"

class OrderItem(SQLModel, table=True):
    __tablename__ = "orders_items"

    id: int = Field(default=None, primary_key=True)
    order_id: int = Field(default=None, foreign_key="orders.id")
    menu_item_id: int = Field(default=None, foreign_key="menu.id")
    quantity: int = Field(default=1)

    #order: Optional["Order"] = Relationship(back_populates="items")

class Order(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    place_id: dict = Field(sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.now)
    trans_id:int = Field(sa_column=Column(INTEGER))
    payment_method: PaymentMethod = Field(default=PaymentMethod.CARD_ONLINE)
    status: OrderStatus = Field(default=OrderStatus.WAITING_PAYMENT)
    total_price: float = Field(default=0.0)

    __tablename__ = "orders"
    #items: List[OrderItem] = Relationship(back_populates="order")


# from typing import Optional, List
# from sqlmodel import Field, SQLModel, Relationship

# class OrderItem(SQLModel, table=True):
#     __tablename__ = "orders_items"
#     id: Optional[int] = Field(default=None, primary_key=True)
#     order_id: Optional[int] = Field(default=None, foreign_key="orders.id")
#     menu_item_id: Optional[int] = Field(default=None, foreign_key="menu.id")
#     quantity: int = Field(default=1)

#     order: Optional["Order"] = Relationship(back_populates="items")


# class Order(SQLModel, table=True):
#     __tablename__ = "orders"
#     id: Optional[int] = Field(default=None, primary_key=True)
#     passenger_name: str
#     seat_number: str

#     items: List[OrderItem] = Relationship(back_populates="order")
