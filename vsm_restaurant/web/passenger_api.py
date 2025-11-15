"""
API для пассажиров.

Содержит endpoints для:
- Просмотра доступного меню
- Просмотра статуса своего заказа
- Отмены заказа
"""
from fastapi import APIRouter, HTTPException
from sqlmodel import select, Session, func
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem, OrderStatus
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.schemas.passenger import (
    OrderStatusResponse, 
    PassengerOrderStatus, 
    PassengerOrderHistory
)
from vsm_restaurant.schemas.orders import OrderItemOut
from vsm_restaurant.services.estimation import estimate_completion_time
from typing import List

router = APIRouter()

@router.get("/passenger/order/{order_id}", response_model=OrderStatusResponse)
def get_order_status(order_id: int, session: SessionDep):
    """
    Получение статуса заказа по ID
    Пассажир может отслеживать прогресс своего заказа
    """
    order = session.get(Order, order_id)
    if not order:
        return OrderStatusResponse(
            success=False,
            message="Order not found"
        )
    
    # Получаем элементы заказа
    # order_items = session.exec(
    #     select(OrderItem).where(OrderItem.order_id == order_id)
    # ).all()
    items_with_details= []
    for item in order.items:
        menu_item = session.get(MenuItemModel, item.menu_item_id)
        items_with_details.append(OrderItemOut(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            menu_item= menu_item  
        ))

    # Получаем детали блюд
    # items_with_details = []
    # for item in order.items:
    #     menu_item = session.get(MenuItemModel, item.menu_item_id)
    #     items_with_details.append(OrderItemOut(
    #         id=item.id,
    #         menu_item_id=item.menu_item_id,
    #         quantity=item.quantity,
    #         menu_item=menu_item
    #     ))
    
    # Оцениваем время готовности
    estimated_time = estimate_completion_time(session, order_id)
    
    order_status = PassengerOrderStatus(
        order_id=order.id,
        place_id=order.place_id,
        status=order.status,
        total_price=order.total_price,
        created_at=order.created_at,
        estimated_time=estimated_time,
        items=items_with_details
    )
    
    return OrderStatusResponse(
        success=True,
        order=order_status,
        message=f"Order {order_id} status: {order.status.value}"
    )

@router.get("/passenger/orders/{place_id}", response_model=List[PassengerOrderHistory])
def get_order_history(place_id: str, session: SessionDep, limit: int = 10):
    """
    История заказов по месту (place_id)
    Пассажир может видеть свои предыдущие заказы
    """
    orders = session.exec(
        select(Order)
        .where(Order.place_id == place_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    
    history = []
    for order in orders:
        # Считаем количество позиций в заказе
        item_count = session.exec(
            select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
        ).first()
        
        history.append(PassengerOrderHistory(
            order_id=order.id,
            status=order.status,
            total_price=order.total_price,
            created_at=order.created_at,
            item_count=item_count or 0
        ))
    
    return history

@router.post("/passenger/order/{order_id}/cancel")
def cancel_order(order_id: int, session: SessionDep):
    """
    Отмена заказа пассажиром
    Можно отменить только если заказ еще не начали готовить
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем, можно ли отменить заказ
    cancellable_statuses = [OrderStatus.WAITING_PAYMENT, OrderStatus.PAID]
    
    if order.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel order in status: {order.status.value}"
        )
    
    # Проверяем, не начали ли уже готовить
    from sqlmodel import select
    from ..db.cooking_task import CookingTask, CookingStatus
    
    cooking_tasks = session.exec(
        select(CookingTask)
        .where(CookingTask.order_id == order_id)
        .where(CookingTask.status != CookingStatus.QUEUED)
    ).first()
    
    if cooking_tasks:
        raise HTTPException(
            status_code=400, 
            detail="Cannot cancel order - cooking already started"
        )
    
    # Отменяем заказ
    order.status = OrderStatus.CANCELLED
    
    # Если была онлайн-оплата, инициируем возврат
    if order.payment_method == "card_online" and order.status == OrderStatus.PAID:
        # В реальной системе здесь был бы вызов API возврата
        print(f"Refund initiated for order {order_id}")
    
    session.commit()
    
    return {
        "success": True,
        "message": f"Order {order_id} cancelled successfully",
        "refund_initiated": order.payment_method == "card_online"
    }

@router.get("/passenger/menu/available")
def get_available_menu(session: SessionDep):
    """
    Получение доступного меню с учетом остатков ингредиентов
    Пассажир видит только то, что можно заказать прямо сейчас
    """
    from sqlmodel import select
    from ..services.availability import check_menu_item_availability
    
    all_menu_items = session.exec(select(MenuItemModel)).all()
    
    available_items = []
    for item in all_menu_items:
        if check_menu_item_availability(session, item.id):
            available_items.append({
                "id": item.id,
                "name": item.name,
                "price": float(item.price),
                "composition": item.composition
            })
    
    return {
        "available_items": available_items,
        "total_available": len(available_items),
        "timestamp": "2024-01-01T00:00:00Z"  # В реальной системе - текущее время
    }