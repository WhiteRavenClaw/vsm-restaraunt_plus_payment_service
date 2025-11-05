from sqlmodel import Session, select
from ..db.cooking_task import CookingTask, CookingStatus
from ..db.orders import Order
import datetime

def estimate_completion_time(session: Session, order_id: int) -> str:
    """
    Простая оценка времени готовности заказа
    В реальной системе здесь была бы сложная логика
    """
    order = session.get(Order, order_id)
    if not order:
        return "Unknown"
    
    # Получаем задачи готовки для заказа
    tasks = session.exec(
        select(CookingTask).where(CookingTask.order_id == order_id)
    ).all()
    
    if not tasks:
        return "Not started"
    
    # Анализируем статусы задач
    statuses = [task.status for task in tasks]
    
    if all(status == CookingStatus.DELIVERED for status in statuses):
        return "Delivered"
    elif all(status == CookingStatus.READY for status in statuses):
        return "Ready for delivery"
    elif any(status == CookingStatus.COOKING for status in statuses):
        return "Cooking - ~15-20 min"
    elif all(status == CookingStatus.QUEUED for status in statuses):
        return "In queue - ~20-25 min"
    else:
        return "Preparing - ~10-15 min"