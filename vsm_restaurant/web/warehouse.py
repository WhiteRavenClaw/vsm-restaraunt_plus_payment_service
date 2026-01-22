from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from vsm_restaurant.db.menu import IngredientModel
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.schemas.menu import (
    IngredientCreate,
    IngredientOut,
    IngredientUpdate,
)

router = APIRouter()
templates = Jinja2Templates(directory="vsm_restaurant/web/templates")


def serialize_ingredient(model: IngredientModel) -> IngredientOut:
    return IngredientOut(
        id=model.id,
        name=model.name,
        stock=model.stock,
    )


@router.get("/warehouse", response_class=HTMLResponse)
async def warehouse_page(request: Request):
    return templates.TemplateResponse(
        "warehouse.html",
        {
            "request": request,
        },
    )


@router.get("/склад", include_in_schema=False)
async def warehouse_page_cyrillic_alias():
    return RedirectResponse(url="/warehouse", status_code=307)


@router.get("/warehouse/api/ingredients", response_model=list[IngredientOut])
async def warehouse_list_ingredients(session: SessionDep):
    result = session.exec(select(IngredientModel))
    return [serialize_ingredient(record) for record in result]


@router.post("/warehouse/api/ingredients", response_model=IngredientOut)
async def warehouse_create_ingredient(
    payload: IngredientCreate,
    session: SessionDep,
):
    model = IngredientModel(**payload.dict())
    session.add(model)
    session.commit()
    session.refresh(model)
    return serialize_ingredient(model)


@router.put(
    "/warehouse/api/ingredients/{ingredient_id}",
    response_model=IngredientOut,
)
async def warehouse_update_ingredient(
    ingredient_id: int,
    payload: IngredientUpdate,
    session: SessionDep,
):
    model = session.get(IngredientModel, ingredient_id)
    if not model:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model, key, value)

    session.add(model)
    session.commit()
    session.refresh(model)
    return serialize_ingredient(model)


@router.delete("/warehouse/api/ingredients/{ingredient_id}")
async def warehouse_delete_ingredient(
    ingredient_id: int,
    session: SessionDep,
):
    model = session.get(IngredientModel, ingredient_id)
    if not model:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    session.delete(model)
    session.commit()
    return {"detail": "Ingredient deleted"}

