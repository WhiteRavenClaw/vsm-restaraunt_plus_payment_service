from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="vsm_restaurant/web/templates")


@router.get("/passenger", response_class=HTMLResponse)
async def passenger_page(request: Request):
    return templates.TemplateResponse("passenger.html", {"request": request})


@router.get("/пассажир", include_in_schema=False)
async def passenger_page_cyrillic_alias():
    return RedirectResponse(url="/passenger", status_code=307)

