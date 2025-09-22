from fastapi import APIRouter
from sqlmodel import select
from vsm_restaurant.db import MenuItemModel
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db import  IngredientModel

router = APIRouter()

@router.get("/ingredients")
async def get_ingredients(session: SessionDep):
    ingredients = session.exec(select(IngredientModel))
    return list(ingredients)