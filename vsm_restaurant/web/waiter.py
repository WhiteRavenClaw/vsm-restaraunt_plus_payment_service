from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="vsm_restaurant/web/templates")


@router.get("/waiter", response_class=HTMLResponse)
async def waiter_page(request: Request):
    return templates.TemplateResponse("waiter.html", {"request": request})


@router.get("/официант", include_in_schema=False)
async def waiter_page_cyrillic_alias():
    return RedirectResponse(url="/waiter", status_code=307)

