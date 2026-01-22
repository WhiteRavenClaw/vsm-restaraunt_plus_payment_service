from typing import List

from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import INTEGER, VARCHAR
from sqlmodel import Field, SQLModel, Relationship

class IngredientModel(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(sa_column=Column(VARCHAR(255)))
    stock: int = Field(sa_column=Column(INTEGER))

    __tablename__ = "ingredients"

class MenuItemModel(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(sa_column=Column(VARCHAR(255)))
    price: float = Field(sa_column=Column(Numeric(10, 2)))
    composition: list[dict] | None = Field(sa_column=Column(JSONB), default=None)

    __tablename__ = "menu"

    order_items: List["OrderItem"] = Relationship(back_populates="menu_item")
    
