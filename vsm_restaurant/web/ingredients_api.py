from fastapi import APIRouter, Header, Depends, HTTPException
from sqlmodel import select
from vsm_restaurant.db.menu import IngredientModel
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.schemas.menu import MenuItemCreate, MenuItemOut, IngredientCreate, IngredientOut, IngredientUpdate

router = APIRouter()
STATIC_TOKEN = "1w348995u85349i3i230irejgi21-0-1dk"

def check_token(authorization: str = Header(...)):
    if authorization != f"Bearer {STATIC_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/ingredients", response_model=list[IngredientOut])
async def list_ingredients(session: SessionDep):
    ingredients = session.exec(select(IngredientModel))
    return [
        IngredientOut(
            id=ingredient.id,
            name=ingredient.name,
            stock=ingredient.stock
        )
        for ingredient in ingredients
    ]

@router.post("/ingredients", response_model=IngredientOut, dependencies=[Depends(check_token)])
async def create_ingredient(item: IngredientCreate, session: SessionDep):
    db_item = IngredientModel(**item.dict())
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return IngredientOut(
        id=db_item.id,
        name=db_item.name,
        stock=db_item.stock
    )

@router.put("/ingredients/{ingredient_id}", response_model=IngredientOut, dependencies=[Depends(check_token)])
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
    return IngredientOut(
        id=db_item.id,
        name=db_item.name,
        stock=db_item.stock
    )

@router.delete("/ingredients/{ingredient_id}", dependencies=[Depends(check_token)])
async def delete_ingredient(ingredient_id: int, session: SessionDep):
    db_item = session.get(IngredientModel, ingredient_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    session.delete(db_item)
    session.commit()
    return {"detail": "Ingredient deleted"}