from fastapi import APIRouter,Depends, HTTPException, Header,Security
from sqlmodel import select
from vsm_restaurant.db import MenuItemModel
from vsm_restaurant.db.menu import MenuItemCreate
from vsm_restaurant.dependencies import SessionDep



router = APIRouter()
STATIC_TOKEN = "1w348995u85349i3i230irejgi21-0-1dk"
#API_KEY_NAME = "Authorization"
#api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
def check_token(authorization: str = Header(...)):
    if authorization != f"Bearer {STATIC_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
#public all
@router.get("/menu")
async def list_menu(session: SessionDep):
    result = session.exec(select(MenuItemModel))
    return list(result)
#add
#@router.post("/menu", dependencies=[Depends(check_token)])
#async def create_menu_item(item: MenuItemModel, session: SessionDep):
#    session.add(item)
#    session.commit()
#    session.refresh(item)
#    return item
@router.post("/menu", dependencies=[Depends(check_token)])
async def create_menu_item(item: MenuItemCreate, session: SessionDep):
    db_item = MenuItemModel(**item.dict())  # создаём запись в БД
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

#upload
@router.put("/menu/{item_id}", dependencies=[Depends(check_token)])
async def update_menu_item(item_id: int, item: MenuItemModel, session: SessionDep):
    db_item = session.get(MenuItemModel, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    db_item.name = item.name
    db_item.price = item.price
    db_item.composition = item.composition
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
#delete
@router.delete("/menu/{item_id}", dependencies=[Depends(check_token)])
async def delete_menu_item(item_id: int, session: SessionDep):
    db_item = session.get(MenuItemModel, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    session.delete(db_item)
    session.commit()
    return {"ok": True}