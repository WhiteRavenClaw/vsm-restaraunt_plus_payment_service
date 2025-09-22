from fastapi import APIRouter
from sqlmodel import select
from vsm_restaurant.db import MenuItemModel
from vsm_restaurant.dependencies import SessionDep

router = APIRouter()

@router.get("/menu")
async def list_menu(session: SessionDep):
    result = session.exec(select(MenuItemModel))
    return list(result)
