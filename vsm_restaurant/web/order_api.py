"""
API для работы с заказами.

Содержит endpoints для:
- Создания заказов (публичный endpoint для пассажиров)
- Просмотра списка заказов
- Интеграции с платежной системой
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import select, Session
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem, OrderStatus, PaymentMethod
from vsm_restaurant.db.cooking_task import CookingTask, CookingStatus
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.schemas.orders import OrderCreate, OrderOut
import httpx
from vsm_restaurant.services.availability import check_menu_item_availability, reserve_ingredients
from vsm_restaurant.services.payment_timeout import set_payment_timeout
from vsm_restaurant.settings import Settings
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_payment_service_url() -> str:
    """Получает URL платежного сервиса из настроек"""
    settings = Settings()
    return getattr(settings, 'payment_service_url', 'http://payment-service:8001')

@router.get("/orders", response_model=list[OrderOut])
def list_orders(session: SessionDep):
    orders = session.exec(select(Order)).all()
    result = []
    for order in orders:
        items_with_details = []
        for item in order.items:
            items_with_details.append({
                "id": item.id,
                "menu_item_id":item.menu_item_id,
                "quantity": item.quantity,
                "menu_item": item.menu_item
            })
        result.append(OrderOut(
            id=order.id,
            place_id=order.place_id,
            created_at=order.created_at,
            payment_method=order.payment_method,
            status=order.status,
            total_price=order.total_price,
            payment_link=order.payment_link,
            items=items_with_details
        ))
    return result

@router.post("/orders",response_model=dict)
async def create_order(order_data: OrderCreate, session: SessionDep, background_tasks: BackgroundTasks):
    try:
        logger.info(f"Creating order: place_id={order_data.place_id}, payment_method={order_data.payment_method}, items={order_data.items}")
        
        # Проверяем доступность блюд и рассчитываем стоимость
        total_price = 0.0
        menu_items = []
        
        for item in order_data.items:
            menu_item = session.get(MenuItemModel, item.menu_item_id)
            if not menu_item:
                logger.error(f"Menu item {item.menu_item_id} not found")
                raise HTTPException(status_code=404, detail=f"Menu item {item.menu_item_id} not found")
            if not check_menu_item_availability(session, item.menu_item_id):
                logger.error(f"Menu item {menu_item.name} is not available")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Menu item {menu_item.name} is not available"
                )
            
            # Проверить доступность ингредиентов
            # Конвертируем price в float, так как Numeric возвращает Decimal
            price = float(menu_item.price) if menu_item.price is not None else 0.0
            total_price += price * item.quantity
            menu_items.append(menu_item)
        
        logger.info(f"Total price calculated: {total_price}")
        
        # Создаем заказ
        # Для всех способов оплаты начальный статус - WAITING_PAYMENT
        # Для онлайн оплаты - ожидание оплаты через платежную систему
        # Для наличных/терминала - ожидание подтверждения оплаты официантом
        order = Order(
            place_id=order_data.place_id,
            payment_method=order_data.payment_method,
            total_price=total_price,
            status=OrderStatus.WAITING_PAYMENT
        )
        
        session.add(order)
        session.commit()
        session.refresh(order)
        logger.info(f"Order created with id: {order.id}")
        
        # Создаем элементы заказа
        for item_data in order_data.items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data.menu_item_id,
                quantity=item_data.quantity
            )
            session.add(order_item)
        
        # Коммитим элементы заказа перед логикой оплаты
        session.commit()
        logger.info(f"Order items created for order {order.id}")
        
        # Логика оплаты
        if order.payment_method in [PaymentMethod.CARD_ONLINE, PaymentMethod.SBP]:
            try:
                logger.info(f"Processing online payment for order {order.id}")
                settings = Settings()
                payment_url = get_payment_service_url()
                payment_type = "sbp" if order.payment_method == PaymentMethod.SBP else "card"
                logger.info(f"Calling payment service: {payment_url}/create, type={payment_type}")
                
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{payment_url}/create",
                        json={"order_id": order.id, "amount": total_price, "type": payment_type},
                        timeout=10.0
                    )
                    r.raise_for_status()
                    payment_data = r.json()
                
                # Устанавливаем payment_link и timeout, затем коммитим все вместе
                order.payment_link = payment_data.get("payment_link")
                set_payment_timeout(session, order, settings.payment_timeout_minutes)
                # set_payment_timeout уже делает commit, но мы можем сделать еще один для надежности
                # session.commit()
                logger.info(f"Payment link created for order {order.id}: {order.payment_link}")
                return {
                    "order_id": order.id,
                    "payment_link": order.payment_link,
                    "status": "waiting_payment",
                    "timeout_minutes": settings.payment_timeout_minutes,
                    "payment_method": order.payment_method.value
                }
            except httpx.HTTPError as e:
                logger.error(f"HTTP error calling payment service: {e}", exc_info=True)
                # Удаляем элементы заказа перед удалением заказа
                try:
                    order_items = session.exec(
                        select(OrderItem).where(OrderItem.order_id == order.id)
                    ).all()
                    for item in order_items:
                        session.delete(item)
                    session.delete(order)
                    session.commit()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}", exc_info=True)
                    session.rollback()
                raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")
            except Exception as e:
                logger.error(f"Payment service error: {e}", exc_info=True)
                # Удаляем элементы заказа перед удалением заказа
                try:
                    order_items = session.exec(
                        select(OrderItem).where(OrderItem.order_id == order.id)
                    ).all()
                    for item in order_items:
                        session.delete(item)
                    session.delete(order)
                    session.commit()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}", exc_info=True)
                    session.rollback()
                raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")
        
        # Для постоплаты (наличные, карта терминал) заказ создается со статусом WAITING_PAYMENT
        # Задачи на готовку будут созданы после подтверждения оплаты официантом
        else:
            logger.info(f"Order {order.id} created with offline payment method, waiting for waiter confirmation")
            return {
                "order_id": order.id,
                "status": "waiting_payment",
                "payment_method": order.payment_method.value,
                "message": "Ожидает подтверждения оплаты официантом"
            }
                
    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating order: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, session: SessionDep):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Получаем элементы заказа с информацией о блюдах
    order_items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()
    
    items_with_details = []
    for item in order_items:
        menu_item = session.get(MenuItemModel, item.menu_item_id)
        items_with_details.append({
            "id": item.id,
            "menu_item_id": item.menu_item_id,
            "quantity": item.quantity,
            "menu_item": menu_item
        })
    
    return OrderOut(
        id=order.id,
        place_id=order.place_id,
        created_at=order.created_at,
        payment_method=order.payment_method,
        status=order.status,
        total_price=order.total_price,
        payment_link=order.payment_link,
        items=items_with_details
    )