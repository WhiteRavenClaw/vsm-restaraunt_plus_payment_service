from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel, Relationship

class CookingStatus(str, Enum):
    QUEUED = "queued"
    COOKING = "cooking"
    READY = "ready"
    DELIVERING = "delivering"
    DELIVERED = "delivered"

class CookingTask(SQLModel, table=True):
    __tablename__ = "cooking_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    menu_item_id: int = Field(foreign_key="menu.id")
    created_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime))
    status: CookingStatus = Field(default=CookingStatus.QUEUED)
    order: Optional["Order"] = Relationship(back_populates="cooking_tasks")
    menu_item: Optional["MenuItemModel"] = Relationship()
    # УБЕРИ отношения
