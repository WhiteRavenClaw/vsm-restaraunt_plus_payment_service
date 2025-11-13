from fastapi import APIRouter, Depends, HTTPException,BackgroundTasks
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
#PAYMENT_SERVICE_URL = "http://payment-service:8001"
def get_payment_service_url():
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
    # Проверяем доступность блюд и рассчитываем стоимость
    total_price = 0.0
    menu_items = []
    
    for item in order_data.items:
        menu_item = session.get(MenuItemModel, item.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item {item.menu_item_id} not found")
        if not check_menu_item_availability(session, item.menu_item_id):
            raise HTTPException(
                status_code=400, 
                detail=f"Menu item {menu_item.name} is not available"
            )
           
        
        
        # Проверить доступность ингредиентов
        total_price += menu_item.price * item.quantity
        menu_items.append(menu_item)
    
    # Создаем заказ
    order = Order(
        place_id=order_data.place_id,
        payment_method=order_data.payment_method,
        total_price=total_price,
        status=OrderStatus.WAITING_PAYMENT if order_data.payment_method in [PaymentMethod.CARD_ONLINE, PaymentMethod.SBP] else OrderStatus.PAID
    )
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    # Создаем элементы заказа
    for item_data in order_data.items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity
        )
        session.add(order_item)
    
    # Логика оплаты
    if order.payment_method in [PaymentMethod.CARD_ONLINE, PaymentMethod.SBP]:
        try:
            settings = Settings()
            set_payment_timeout(session, order, settings.payment_timeout_minutes)
            payment_url = get_payment_service_url()
            payment_type = "sbp" if order.payment_method == PaymentMethod.SBP else "card"
            r = httpx.post(
                f"{payment_url}/create",
                json={"order_id": order.id, "amount": total_price, "type": payment_type}
            )
            r.raise_for_status()
            payment_data = r.json()
            order.payment_link = payment_data.get("payment_link")
            session.commit()
            return {
                "order_id": order.id,
                "payment_link": order.payment_link,
                "status": "waiting_payment",
                "timeout_minutes": settings.payment_timeout_minutes,
                "payment_method": order.payment_method.value
            }
        except Exception as e:
            logger.error(f"Payment service error: {e}")
            session.delete(order)
            session.commit()
            raise HTTPException(status_code=500, detail=f"Payment service error: {e}")
    
    # Для постоплаты (наличные, карта терминал) сразу создаем задачи на готовку
    else:
        for item_data in order_data.items:
            reserve_ingredients(session, item_data.menu_item_id)
            task = CookingTask(
                order_id=order.id,
                menu_item_id=item_data.menu_item_id,
                status=CookingStatus.QUEUED
            )
            session.add(task)
        session.commit()
        return {"order_id": order.id, "status": "paid_and_queued"}
    
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