from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlmodel import select, Session
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderStatus, PaymentMethod
from vsm_restaurant.services.payment_timeout import check_payment_timeout, set_payment_timeout
from vsm_restaurant.settings import Settings
from pydantic import BaseModel
from datetime import datetime
import httpx

router = APIRouter()

class PaymentMethodSwitch(BaseModel):
    new_payment_method: PaymentMethod

class OrderStatusResponse(BaseModel):
    order_id: int
    status: OrderStatus
    can_switch_payment: bool
    time_remaining: Optional[str] = None
    is_expired: bool = False

@router.get("/orders/{order_id}/payment-status", response_model=OrderStatusResponse)
async def get_payment_status(order_id: int, session: SessionDep):
    """Получение статуса оплаты с информацией о таймауте"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем таймаут
    is_expired = await check_payment_timeout(session, order_id)
    if is_expired and order.status == OrderStatus.WAITING_PAYMENT:
        order.status = OrderStatus.CANCELLED
        session.commit()
    
    # Рассчитываем оставшееся время
    time_remaining = None
    if (order.status == OrderStatus.WAITING_PAYMENT and 
        order.payment_timeout_at):
        remaining = order.payment_timeout_at - datetime.now()
        if remaining.total_seconds() > 0:
            minutes = int(remaining.total_seconds() // 60)
            time_remaining = f"{minutes} min"
    
    # Можно ли сменить способ оплаты
    can_switch_payment = (
        order.status == OrderStatus.WAITING_PAYMENT and 
        not is_expired
    )
    
    return OrderStatusResponse(
        order_id=order.id,
        status=order.status,
        can_switch_payment=can_switch_payment,
        time_remaining=time_remaining,
        is_expired=is_expired
    )

@router.post("/orders/{order_id}/switch-payment")
async def switch_payment_method(
    order_id: int, 
    switch_data: PaymentMethodSwitch,
    session: SessionDep,
    background_tasks: BackgroundTasks
):
    """Смена способа оплаты для заказа"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем условия для смены оплаты
    if order.status != OrderStatus.WAITING_PAYMENT:
        raise HTTPException(
            status_code=400, 
            detail="Cannot switch payment method for order in current status"
        )
    
    # Проверяем таймаут
    if await check_payment_timeout(session, order_id):
        raise HTTPException(
            status_code=400, 
            detail="Payment time has expired. Please create a new order."
        )
    
    # Меняем способ оплаты
    old_method = order.payment_method
    order.payment_method = switch_data.new_payment_method
    order.updated_at = datetime.now()
    
    # Если переключаем на постоплату - сразу подтверждаем оплату
    if switch_data.new_payment_method in [PaymentMethod.CARD_TERMINAL, PaymentMethod.CASH]:
        order.status = OrderStatus.PAID
        order.payment_timeout_at = None  # Сбрасываем таймаут
        
        # Создаем задачи на готовку
        from sqlmodel import select
        from ..db.cooking_task import CookingTask, CookingStatus
        from ..db.menu import OrderItem
        from ..services.availability import reserve_ingredients
        
        order_items = session.exec(
            select(OrderItem).where(OrderItem.order_id == order_id)
        ).all()
        
        for item in order_items:
            # Резервируем ингредиенты
            reserve_ingredients(session, item.menu_item_id)
            
            # Создаем задачу на готовку
            task = CookingTask(
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                status=CookingStatus.QUEUED
            )
            session.add(task)
    
    session.commit()
    
    return {
        "success": True,
        "order_id": order_id,
        "old_payment_method": old_method,
        "new_payment_method": switch_data.new_payment_method,
        "status": order.status,
        "message": "Payment method switched successfully"
    }

@router.post("/orders/{order_id}/extend-timeout")
async def extend_payment_timeout(order_id: int, session: SessionDep):
    """Продление времени оплаты"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != OrderStatus.WAITING_PAYMENT:
        raise HTTPException(
            status_code=400, 
            detail="Can only extend timeout for orders waiting for payment"
        )
    
    # Продлеваем таймаут еще на 15 минут
    settings = Settings()
    set_payment_timeout(session, order, settings.payment_timeout_minutes)
    
    return {
        "success": True,
        "order_id": order_id,
        "new_timeout_at": order.payment_timeout_at.isoformat(),
        "message": "Payment timeout extended"
    }

@router.post("/payments/webhook")
async def payment_webhook(webhook_data: dict, session: SessionDep):
    """Обработка вебхуков от платежной системы с проверкой конфликтов"""
    order_id = webhook_data.get("order_id")
    status = webhook_data.get("status")
    
    if not order_id or not status:
        raise HTTPException(status_code=400, detail="Invalid webhook data")
    
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Проверяем на конфликт: если заказ уже отменен из-за таймаута
    if order.status == OrderStatus.CANCELLED and status == "success":
        # Конфликт: платеж прошел, но заказ отменен
        logger.warning(f"Payment conflict for order {order_id}: payment success but order cancelled")
        
        # Инициируем возврат
        try:
            async with httpx.AsyncClient() as client:
                refund_response = await client.post(
                    f"http://payment-service:8001/refund/{order_id}"
                )
                refund_response.raise_for_status()
                
                return {
                    "status": "refund_initiated",
                    "message": "Order was cancelled due to timeout, refund initiated",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"Failed to initiate refund for order {order_id}: {e}")
            return {
                "status": "refund_failed",
                "message": "Payment received but order was cancelled. Refund may be required manually.",
                "order_id": order_id
            }
    
    # Нормальная обработка успешного платежа
    if status == "success" and order.status == OrderStatus.WAITING_PAYMENT:
        order.status = OrderStatus.PAID
        order.payment_timeout_at = None  # Сбрасываем таймаут
        order.updated_at = datetime.now()
        
        # Создаем задачи на готовку
        from sqlmodel import select
        from ..db.cooking_task import CookingTask, CookingStatus
        from ..db.menu import OrderItem
        from ..services.availability import reserve_ingredients
        
        order_items = session.exec(
            select(OrderItem).where(OrderItem.order_id == order_id)
        ).all()
        
        for item in order_items:
            # Резервируем ингредиенты
            reserve_ingredients(session, item.menu_item_id)
            
            task = CookingTask(
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                status=CookingStatus.QUEUED
            )
            session.add(task)
        
        session.commit()
        
        return {
            "status": "processed",
            "message": "Payment confirmed and order queued for cooking",
            "order_id": order_id
        }
    
    return {"status": "ignored", "message": "Webhook processed but no action taken"}