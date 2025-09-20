import logging

from fastapi import FastAPI

from vsm_restaurant.dependencies import lifespan

from .demo import router as demo_router

logger = logging.getLogger(__name__)

media_location_prefix = "/media/"
app = FastAPI(lifespan=lifespan)

app.include_router(demo_router)

@app.get("/")
async def root():
    return "Hello world"
