"""
Главный модуль FastAPI приложения.

Содержит инициализацию приложения, регистрацию всех роутеров и обработчики событий жизненного цикла.
"""
import logging

from fastapi import FastAPI

from vsm_restaurant.dependencies import lifespan

# API роутеры
from .demo import router as demo_router
from .menu_api import router as menu_router
from .ingredients_api import router as ingredients_router
from .order_api import router as order_router
from .cooking_api import router as cooking_router
from .payment_management_api import router as payment_router
from .waiter_api import router as waiter_api_router
from .passenger_api import router as passenger_router

# UI роутеры
from .warehouse_ui import router as warehouse_router
from .kitchen_ui import router as kitchen_router
from .passenger_ui import router as passenger_ui_router
from .waiter_ui import router as waiter_ui_router
import asyncio
from sqlmodel import Session
from vsm_restaurant.services.payment_timeout import PaymentTimeoutService




logger = logging.getLogger(__name__)

media_location_prefix = "/media/"
app = FastAPI(lifespan=lifespan)

# Регистрация API роутеров
app.include_router(demo_router)
app.include_router(menu_router)
app.include_router(ingredients_router)
app.include_router(order_router)
app.include_router(cooking_router)
app.include_router(payment_router)
app.include_router(waiter_api_router)
app.include_router(passenger_router)

# Регистрация UI роутеров
app.include_router(warehouse_router)
app.include_router(kitchen_router)
app.include_router(passenger_ui_router)
app.include_router(waiter_ui_router)

@app.get("/")
async def root():
    """Корневой endpoint для проверки работоспособности сервиса"""
    return {"message": "VSM Restaurant API", "status": "running"}

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    # Запускаем сервис таймаутов для автоматической отмены просроченных заказов
    timeout_service = PaymentTimeoutService(app.state.settings)
    
    def session_factory():
        return Session(app.state.engine)
    
    asyncio.create_task(timeout_service.start_cleanup_task(session_factory))
    
    # Сохраняем сервис в состоянии приложения
    app.state.timeout_service = timeout_service
    logger.info("Payment timeout service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения"""
    if hasattr(app.state, 'timeout_service'):
        app.state.timeout_service.stop()
        logger.info("Payment timeout service stopped")
