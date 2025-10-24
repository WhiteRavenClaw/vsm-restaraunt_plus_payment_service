from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[int] = Field(default=None, foreign_key="orders.id")
    menu_item_id: Optional[int] = Field(default=None, foreign_key="menu.id")
    quantity: int = Field(default=1)

    order: Optional["Order"] = Relationship(back_populates="items")


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: Optional[int] = Field(default=None, primary_key=True)
    passenger_name: str
    seat_number: str

    items: List[OrderItem] = Relationship(back_populates="order")
