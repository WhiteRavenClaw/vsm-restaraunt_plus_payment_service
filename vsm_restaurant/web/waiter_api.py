"""
API для официанта.

Содержит endpoints для:
- Просмотра списка заказов с фильтрацией
- Просмотра деталей заказа
- Подтверждения оплаты (для наличных/терминала)
- Обновления статуса доставки заказа
"""
from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem, OrderStatus, PaymentMethod
from vsm_restaurant.db.cooking_task import CookingTask, CookingStatus
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.schemas.waiter import WaiterOrderSummary, DeliveryUpdate, PaymentReceived
from vsm_restaurant.schemas.orders import OrderOut, OrderItemOut
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/waiter/orders", response_model=List[WaiterOrderSummary])
def list_orders_for_waiter(
    session: SessionDep, 
    status: str = None,
    place_id: str = None
):
    """
    Список заказов для официанта
    - Можно фильтровать по статусу и месту
    - По умолчанию показываются все заказы кроме отмененных
    """
    try:
        query = select(Order)
        
        # По умолчанию показываем все заказы кроме отмененных
        if status is None or status == "":
            # Фильтруем по разрешенным статусам (исключаем CANCELLED)
            # Используем список разрешенных статусов вместо != для избежания проблем с enum
            allowed_statuses = [
                OrderStatus.WAITING_PAYMENT,
                OrderStatus.PAID,
                OrderStatus.COOKING,
                OrderStatus.PARTIALLY_DELIVERED,
                OrderStatus.COMPLETED
            ]
            query = query.where(Order.status.in_(allowed_statuses))
        else:
            # Преобразуем строку в OrderStatus
            try:
                order_status = OrderStatus(status)
                query = query.where(Order.status == order_status)
            except ValueError:
                # Если статус невалидный, возвращаем пустой список
                return []
        
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
            
            # Конвертируем total_price в float, если это Decimal
            total_price = float(order.total_price) if order.total_price is not None else 0.0
            
            result.append(WaiterOrderSummary(
                id=order.id,
                place_id=order.place_id,
                status=order.status,
                total_price=total_price,
                payment_method=order.payment_method,
                created_at=order.created_at,
                item_count=item_count or 0
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error in list_orders_for_waiter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/waiter/orders/{order_id}", response_model=OrderOut)
def get_order_details(order_id: int, session: SessionDep):
    """
    Детальная информация о заказе для официанта
    """
    try:
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
            if menu_item:
                # Конвертируем menu_item в MenuItemOut с правильными типами
                from vsm_restaurant.schemas.menu import MenuItemOut
                menu_item_price = float(menu_item.price) if menu_item.price is not None else 0.0
                menu_item_out = MenuItemOut(
                    id=menu_item.id,
                    name=menu_item.name,
                    price=menu_item_price,
                    composition=menu_item.composition
                )
            else:
                menu_item_out = None
            
            items_with_details.append(OrderItemOut(
                id=item.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                menu_item=menu_item_out
            ))
        
        # Конвертируем total_price в float, если это Decimal
        total_price = float(order.total_price) if order.total_price is not None else 0.0
        
        return OrderOut(
            id=order.id,
            place_id=order.place_id,
            created_at=order.created_at,
            payment_method=order.payment_method,
            status=order.status,
            total_price=total_price,
            payment_link=order.payment_link,
            items=items_with_details
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_order_details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.patch("/waiter/orders/{order_id}/status")
def update_order_status(order_id: int, update: DeliveryUpdate, session: SessionDep):
    """
    Обновление статуса заказа
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем валидность перехода статусов
    valid_transitions = {
        OrderStatus.PAID: [OrderStatus.COOKING, OrderStatus.PARTIALLY_DELIVERED],
        OrderStatus.COOKING: [OrderStatus.PARTIALLY_DELIVERED],
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

@router.post("/waiter/orders/{order_id}/payment")
def confirm_payment_received(order_id: int, payment_data: PaymentReceived, session: SessionDep):
    """
    Подтверждение получения оплаты (для наличных и карты терминал)
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем, что это постоплата
    if order.payment_method not in [PaymentMethod.CARD_TERMINAL, PaymentMethod.CASH]:
        raise HTTPException(
            status_code=400, 
            detail="This order is not for cash/terminal payment"
        )
    
    # Проверяем, что заказ ожидает оплаты
    if order.status != OrderStatus.WAITING_PAYMENT:
        raise HTTPException(
            status_code=400, 
            detail=f"Can only confirm payment for orders with status WAITING_PAYMENT. Current status: {order.status}"
        )
    
    # Подтверждаем оплату - меняем статус на PAID
    order.status = OrderStatus.PAID
    
    # Создаем задачи на готовку после подтверждения оплаты
    order_items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()
    
    for item in order_items:
        # Резервируем ингредиенты
        from vsm_restaurant.services.availability import reserve_ingredients
        reserve_ingredients(session, item.menu_item_id)
        
        # Создаем задачу на готовку
        task = CookingTask(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            status=CookingStatus.QUEUED
        )
        session.add(task)
    
    # Логируем подтверждение оплаты
    logger.info(f"Payment confirmed for order {order_id}: {payment_data.payment_method}")
    
    session.commit()
    session.refresh(order)
    
    return {
        "status": "payment_confirmed", 
        "order_id": order_id,
        "new_status": order.status.value,
        "payment_method": payment_data.payment_method
    }

@router.get("/waiter/tasks")
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

