from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem, OrderStatus, PaymentMethod
from vsm_restaurant.db.cooking_task import CookingTask, CookingStatus
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.schemas.orders import OrderCreate, OrderOut
import httpx

router = APIRouter()
PAYMENT_SERVICE_URL = "http://payment-service:8001"

@router.get("/orders", response_model=list[OrderOut])
def list_orders(session: SessionDep):
    orders = session.exec(select(Order)).all()
    return orders

@router.post("/orders")
def create_order(order_data: OrderCreate, session: SessionDep):
    # Проверяем доступность блюд и рассчитываем стоимость
    total_price = 0.0
    menu_items = []
    
    for item in order_data.items:
        menu_item = session.get(MenuItemModel, item.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item {item.menu_item_id} not found")
        
        # TODO: Проверить доступность ингредиентов
        total_price += menu_item.price * item.quantity
        menu_items.append(menu_item)
    
    # Создаем заказ
    order = Order(
        place_id=order_data.place_id,
        payment_method=order_data.payment_method,
        total_price=total_price,
        status=OrderStatus.WAITING_PAYMENT if order_data.payment_method == PaymentMethod.CARD_ONLINE else OrderStatus.PAID
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
    if order.payment_method == PaymentMethod.CARD_ONLINE:
        try:
            r = httpx.post(f"{PAYMENT_SERVICE_URL}/create", params={"order_id": order.id})
            r.raise_for_status()
            payment_data = r.json()
            order.payment_link = payment_data.get("payment_link")
            session.commit()
            return {"order_id": order.id, "payment_link": order.payment_link, "status": "waiting_payment"}
        except Exception as e:
            # Отменяем заказ при ошибке оплаты
            session.delete(order)
            session.commit()
            raise HTTPException(status_code=500, detail=f"Payment service error: {e}")
    
    # Для постоплаты сразу создаем задачи на готовку
    else:
        for item_data in order_data.items:
            task = CookingTask(
                order_id=order.id,
                menu_item_id=item_data.menu_item_id,
                status=CookingStatus.QUEUED
            )
            session.add(task)
        session.commit()
        return {"order_id": order.id, "status": "paid_and_queued"}