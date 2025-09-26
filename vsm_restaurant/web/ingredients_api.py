from fastapi import APIRouter, Header
from sqlmodel import select
from fastapi import Depends, HTTPException
from vsm_restaurant.db import IngredientModel
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db import IngredientCreate, IngredientUpdate
#from vsm_restaurant.web.menu_api import check_token
router = APIRouter()
STATIC_TOKEN = "1w348995u85349i3i230irejgi21-0-1dk"
def check_token(authorization: str = Header(...)):
    if authorization != f"Bearer {STATIC_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
@router.get("/ingredients")
async def list_ingredients(session: SessionDep):
    ingredients = session.exec(select(IngredientModel))
    return list(ingredients)

@router.post("/ingredients", dependencies=[Depends(check_token)])
async def create_ingredient(item: IngredientCreate, session: SessionDep):
    db_item = IngredientModel(**item.dict())
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

# --- Обновить ингредиент ---
@router.put("/ingredients/{ingredient_id}", dependencies=[Depends(check_token)])
async def update_ingredient(ingredient_id: int, item: IngredientUpdate, session: SessionDep):
    db_item = session.get(IngredientModel, ingredient_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    update_data = item.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

# --- Удалить ингредиент ---
@router.delete("/ingredients/{ingredient_id}", dependencies=[Depends(check_token)])
async def delete_ingredient(ingredient_id: int, session: SessionDep):
    db_item = session.get(IngredientModel, ingredient_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    session.delete(db_item)
    session.commit()
    return {"detail": "Ingredient deleted"}