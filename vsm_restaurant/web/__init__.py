import logging

from fastapi import FastAPI

from vsm_restaurant.dependencies import lifespan

from .demo import router as demo_router
from .menu_api import router as menu_router
from .ingredients_api import router as ingredients_router
from .order_api import router as order_router
from .cooking_api import router as cooking_router
from .payment_api import router as payment_router
from .conductor_api import router as conductor_router
from .passenger_api import router as passenger_router
import asyncio
from sqlmodel import Session
from vsm_restaurant.services.payment_timeout import PaymentTimeoutService




logger = logging.getLogger(__name__)

media_location_prefix = "/media/"
app = FastAPI(lifespan=lifespan)

app.include_router(demo_router)
app.include_router(menu_router)
app.include_router(ingredients_router)
app.include_router(order_router)
app.include_router(cooking_router)
app.include_router(payment_router)
app.include_router(conductor_router)
app.include_router(passenger_router)
@app.get("/")
async def root():
    return "Hello world"

@app.on_event("startup")
async def startup_event():
    # Запускаем сервис таймаутов
    timeout_service = PaymentTimeoutService(app.state.settings)
    
    def session_factory():
        return Session(app.state.engine)
    
    asyncio.create_task(timeout_service.start_cleanup_task(session_factory))
    
    # Сохраняем сервис в состоянии приложения
    app.state.timeout_service = timeout_service

@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, 'timeout_service'):
        app.state.timeout_service.stop()
# timeout_service = PaymentTimeoutService()
# @app.on_event("startup")
# async def startup_event():
#     # Запускаем сервис таймаутов
#     def session_factory():
#         return Session(app.state.engine)
    
#     asyncio.create_task(timeout_service.start_cleanup_task(session_factory))

# @app.on_event("shutdown")
# async def shutdown_event():
#     timeout_service.stop()