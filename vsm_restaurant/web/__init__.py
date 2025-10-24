import logging

from fastapi import FastAPI

from vsm_restaurant.dependencies import lifespan

from .demo import router as demo_router
from .menu_api import router as menu_router
from .ingredients_api import router as ingredients_router
from .order_api import router as order_router





logger = logging.getLogger(__name__)

media_location_prefix = "/media/"
app = FastAPI(lifespan=lifespan)

app.include_router(demo_router)
app.include_router(menu_router)
app.include_router(ingredients_router)
app.include_router(order_router)
@app.get("/")
async def root():
    return "Hello world"


#@app.get("/menu", response_model=list[MenuItemOut])
#async def list_menu(session: SessionDep):
#    result = session.exec(select(MenuItemModel))
#    return list(result)