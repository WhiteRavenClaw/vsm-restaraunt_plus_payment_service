from fastapi import APIRouter, HTTPException
from sqlmodel import select, Session, func
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem, OrderStatus, PaymentMethod
from vsm_restaurant.db.cooking_task import CookingTask, CookingStatus
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.schemas.conductor import ConductorOrderSummary, DeliveryUpdate, PaymentReceived
from vsm_restaurant.schemas.orders import OrderOut, OrderItemOut
from typing import List

router = APIRouter()

@router.get("/conductor/orders", response_model=List[ConductorOrderSummary])
def list_orders_for_delivery(
    session: SessionDep, 
    status: OrderStatus = None,
    place_id: str = None
):
    """
    Список заказов для проводника
    - Можно фильтровать по статусу и месту
    - По умолчанию показываются заказы готовые к доставке
    """
    query = select(Order)
    
    # По умолчанию показываем заказы, которые готовы к доставке
    if status is None:
        query = query.where(
            (Order.status == OrderStatus.PAID) | 
            (Order.status == OrderStatus.COOKING) |
            (Order.status == OrderStatus.PARTIALLY_DELIVERED)
        )
    else:
        query = query.where(Order.status == status)
    
    if place_id:
        query = query.where(Order.place_id == place_id)
    
    query = query.order_by(Order.created_at.desc())
    
    orders = session.exec(query).all()
    
    result = []
    for order in orders:
        # Получаем количество позиций в заказе
        item_count = session.exec(
            select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
        ).first()
        
        result.append(ConductorOrderSummary(
            id=order.id,
            place_id=order.place_id,
            status=order.status,
            total_price=order.total_price,
            payment_method=order.payment_method,
            created_at=order.created_at,
            item_count=item_count or 0
        ))
    
    return result

@router.get("/conductor/orders/{order_id}", response_model=OrderOut)
def get_order_details(order_id: int, session: SessionDep):
    """
    Детальная информация о заказе для проводника
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Получаем элементы заказа
    order_items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()
    
    # Получаем информацию о блюдах
    items_with_details = []
    for item in order_items:
        menu_item = session.get(MenuItemModel, item.menu_item_id)
        items_with_details.append(OrderItemOut(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            menu_item=menu_item
        ))
    
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

@router.patch("/conductor/orders/{order_id}/status")
def update_order_status(order_id: int, update: DeliveryUpdate, session: SessionDep):
    """
    Обновление статуса заказа (доставка)
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем валидность перехода статусов
    valid_transitions = {
        OrderStatus.COOKING: [OrderStatus.PARTIALLY_DELIVERED],
        OrderStatus.PAID: [OrderStatus.PARTIALLY_DELIVERED],  # Если что-то уже готово
        OrderStatus.PARTIALLY_DELIVERED: [OrderStatus.COMPLETED],
    }
    
    current_status = order.status
    new_status = update.status
    
    if (current_status in valid_transitions and 
        new_status not in valid_transitions[current_status]):
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot transition from {current_status} to {new_status}"
        )
    
    order.status = new_status
    
    # Если заказ завершен, обновляем статусы задач готовки
    if new_status == OrderStatus.COMPLETED:
        tasks = session.exec(
            select(CookingTask).where(CookingTask.order_id == order_id)
        ).all()
        for task in tasks:
            if task.status != CookingStatus.DELIVERED:
                task.status = CookingStatus.DELIVERED
                session.add(task)
    
    session.commit()
    session.refresh(order)
    
    return {"status": "updated", "order_id": order_id, "new_status": new_status}

@router.post("/conductor/orders/{order_id}/payment")
def confirm_payment_received(order_id: int, payment_data: PaymentReceived, session: SessionDep):
    """
    Подтверждение получения оплаты (для постоплаты)
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем, что это постоплата
    if order.payment_method not in [PaymentMethod.CARD_TERMINAL, PaymentMethod.CASH]:
        raise HTTPException(
            status_code=400, 
            detail="This order is not for post-payment"
        )
    
    # Проверяем, что заказ уже доставлен или частично доставлен
    if order.status not in [OrderStatus.PARTIALLY_DELIVERED, OrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=400, 
            detail="Can only confirm payment for delivered orders"
        )
    
    # Подтверждаем оплату (меняем статус на завершенный, если еще не завершен)
    if order.status != OrderStatus.COMPLETED:
        order.status = OrderStatus.COMPLETED
    
    # Логируем подтверждение оплаты
    print(f"Payment confirmed for order {order_id}: {payment_data.payment_method}")
    
    session.commit()
    
    return {
        "status": "payment_confirmed", 
        "order_id": order_id, 
        "payment_method": payment_data.payment_method
    }

@router.get("/conductor/tasks")
def list_cooking_tasks(session: SessionDep, status: CookingStatus = None):
    """
    Список задач готовки для мониторинга прогресса
    """
    query = select(CookingTask)
    
    if status:
        query = query.where(CookingTask.status == status)
    
    tasks = session.exec(query.order_by(CookingTask.created_at.asc())).all()
    
    # Добавляем информацию о заказе и блюде
    result = []
    for task in tasks:
        order = session.get(Order, task.order_id)
        menu_item = session.get(MenuItemModel, task.menu_item_id)
        
        result.append({
            "task_id": task.id,
            "order_id": task.order_id,
            "place_id": order.place_id if order else "Unknown",
            "menu_item_name": menu_item.name if menu_item else "Unknown",
            "status": task.status,
            "created_at": task.created_at
        })
    
    return result