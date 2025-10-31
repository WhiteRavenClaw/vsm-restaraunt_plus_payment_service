from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import select
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.schemas.menu import MenuItemCreate, MenuItemOut, IngredientCreate, IngredientOut, IngredientUpdate

router = APIRouter()
STATIC_TOKEN = "1w348995u85349i3i230irejgi21-0-1dk"

def check_token(authorization: str = Header(...)):
    if authorization != f"Bearer {STATIC_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

# Public - get menu
@router.get("/menu", response_model=list[MenuItemOut])
async def list_menu(session: SessionDep):
    result = session.exec(select(MenuItemModel))
    menu_items = list(result)
    # Преобразуем SQLModel в Pydantic вручную
    return [
        MenuItemOut(
            id=item.id,
            name=item.name,
            price=item.price,
            composition=item.composition
        )
        for item in menu_items
    ]

# Admin - create menu item
@router.post("/menu", response_model=MenuItemOut, dependencies=[Depends(check_token)])
async def create_menu_item(item: MenuItemCreate, session: SessionDep):
    db_item = MenuItemModel(**item.dict())
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    # Возвращаем Pydantic модель
    return MenuItemOut(
        id=db_item.id,
        name=db_item.name,
        price=db_item.price,
        composition=db_item.composition
    )

# Admin - update menu item
@router.put("/menu/{item_id}", response_model=MenuItemOut, dependencies=[Depends(check_token)])
async def update_menu_item(item_id: int, item: MenuItemCreate, session: SessionDep):
    db_item = session.get(MenuItemModel, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    update_data = item.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    
    return MenuItemOut(
        id=db_item.id,
        name=db_item.name,
        price=db_item.price,
        composition=db_item.composition
    )

# Admin - delete menu item
@router.delete("/menu/{item_id}", dependencies=[Depends(check_token)])
async def delete_menu_item(item_id: int, session: SessionDep):
    db_item = session.get(MenuItemModel, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    session.delete(db_item)
    session.commit()
    return {"ok": True}