from fastapi import APIRouter, HTTPException
from sqlmodel import select, Session
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderStatus
from vsm_restaurant.db.cooking_task import CookingTask, CookingStatus
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.services.availability import reserve_ingredients
from pydantic import BaseModel

router = APIRouter()

class PaymentWebhook(BaseModel):
    order_id: int
    status: str

@router.post("/payments/webhook")
async def payment_webhook(webhook_data: PaymentWebhook, session: SessionDep):
    order = session.get(Order, webhook_data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if webhook_data.status == "success":
        # Меняем статус заказа на оплачен
        order.status = OrderStatus.PAID
        
        # Создаем задачи на готовку
        from sqlmodel import select
        order_items = session.exec(
            select(OrderItem).where(OrderItem.order_id == order.id)
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
        return {"status": "order_processed"}
    
    return {"status": "webhook_received"}