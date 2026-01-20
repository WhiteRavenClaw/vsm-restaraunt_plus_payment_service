from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from vsm_restaurant.db.menu import MenuItemModel, IngredientModel
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.schemas.menu import MenuItemCreate, MenuItemOut, IngredientOut

router = APIRouter()
templates = Jinja2Templates(directory="vsm_restaurant/web/templates")


@router.get("/kitchen", response_class=HTMLResponse)
async def kitchen_page(request: Request):
    return templates.TemplateResponse("kitchen.html", {"request": request})


@router.get("/кухня", include_in_schema=False)
async def kitchen_page_cyrillic_alias():
    return RedirectResponse(url="/kitchen", status_code=307)


@router.get("/kitchen/api/menu", response_model=list[MenuItemOut])
async def kitchen_list_menu(session: SessionDep):
    result = session.exec(select(MenuItemModel))
    return [
        MenuItemOut(
            id=item.id,
            name=item.name,
            price=item.price,
            composition=item.composition,
        )
        for item in result
    ]


@router.get("/kitchen/api/ingredients", response_model=list[IngredientOut])
async def kitchen_list_ingredients(session: SessionDep):
    result = session.exec(select(IngredientModel))
    return [IngredientOut(id=ing.id, name=ing.name, stock=ing.stock) for ing in result]


@router.post("/kitchen/api/menu", response_model=MenuItemOut)
async def kitchen_create_menu_item(payload: MenuItemCreate, session: SessionDep):
    model = MenuItemModel(**payload.dict())
    session.add(model)
    session.commit()
    session.refresh(model)
    return MenuItemOut(
        id=model.id,
        name=model.name,
        price=model.price,
        composition=model.composition,
    )


@router.put("/kitchen/api/menu/{item_id}", response_model=MenuItemOut)
async def kitchen_update_menu_item(
    item_id: int,
    payload: MenuItemCreate,
    session: SessionDep,
):
    model = session.get(MenuItemModel, item_id)
    if not model:
        raise HTTPException(status_code=404, detail="Menu item not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model, key, value)

    session.add(model)
    session.commit()
    session.refresh(model)
    return MenuItemOut(
        id=model.id,
        name=model.name,
        price=model.price,
        composition=model.composition,
    )


@router.delete("/kitchen/api/menu/{item_id}")
async def kitchen_delete_menu_item(item_id: int, session: SessionDep):
    model = session.get(MenuItemModel, item_id)
    if not model:
        raise HTTPException(status_code=404, detail="Menu item not found")

    session.delete(model)
    session.commit()
    return {"detail": "Menu item deleted"}

