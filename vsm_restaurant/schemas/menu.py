from pydantic import BaseModel
from typing import List, Optional, Dict

class MenuItemOut(BaseModel):
    id: int
    name: str
    price: float
    composition: Optional[List[Dict]] = None

class MenuItemCreate(BaseModel):
    name: str
    price: float
    composition: Optional[List[Dict]] = None

class IngredientOut(BaseModel):
    id: int
    name: str
    stock: int

class IngredientCreate(BaseModel):
    name: str
    stock: int

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    stock: Optional[int] = None