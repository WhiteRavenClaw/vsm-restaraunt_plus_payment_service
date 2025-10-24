from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import VARCHAR, INTEGER
from sqlmodel import Field, SQLModel
from sqlmodel import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

class IngredientModel(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(sa_column=Column(VARCHAR(255)))
    stock: int = Field(sa_column=Column(INTEGER))

    __tablename__ = "ingredients"

class IngredientCreate(BaseModel):
    name: str
    stock: int

class IngredientUpdate(BaseModel):
    name: str | None = None
    stock: int | None = None

class MenuItemModel(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(sa_column=Column(VARCHAR(255)))
    price: float = Field(sa_column=Column(Numeric(10, 2)))
    composition: list[dict] | None = Field(sa_column=Column(JSONB), default=None)

    __tablename__ = "menu"

class MenuItemCreate(BaseModel):
    name: str
    price: float
    composition: Optional[List[Dict]] = None