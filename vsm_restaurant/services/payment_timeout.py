import asyncio
from datetime import datetime, timedelta
from sqlmodel import select, Session
from ..db.orders import Order, OrderStatus, PaymentMethod
from ..settings import Settings
import logging

logger = logging.getLogger(__name__)

class PaymentTimeoutService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.is_running = False
    
    async def start_cleanup_task(self, session_factory):
        """Запускает фоновую задачу очистки просроченных платежей"""
        self.is_running = True
        logger.info("Payment timeout service started")
        
        while self.is_running:
            try:
                await self.cleanup_expired_payments(session_factory)
                await asyncio.sleep(self.settings.cleanup_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in payment cleanup: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    async def cleanup_expired_payments(self, session_factory):
        """Очистка просроченных платежей"""
        try:
            with session_factory() as session:
                expired_orders = session.exec(
                    select(Order).where(
                        Order.status == OrderStatus.WAITING_PAYMENT,
                        Order.payment_timeout_at <= datetime.now()
                    )
                ).all()
                
                for order in expired_orders:
                    await self.handle_expired_payment(session, order)
                
                if expired_orders:
                    logger.info(f"Cleaned up {len(expired_orders)} expired payments")
                    
        except Exception as e:
            logger.error(f"Error cleaning expired payments: {e}")
    
    async def handle_expired_payment(self, session: Session, order: Order):
        """Обработка просроченного платежа"""
        try:
            logger.info(f"Handling expired payment for order {order.id}")
            
            # Помечаем заказ как просроченный
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            
            # Если прилетит вебхук позже - обработаем конфликт
            session.add(order)
            session.commit()
            
            logger.info(f"Order {order.id} cancelled due to payment timeout")
            
        except Exception as e:
            logger.error(f"Error handling expired payment for order {order.id}: {e}")
            session.rollback()
    
    def stop(self):
        """Остановка сервиса"""
        self.is_running = False
        logger.info("Payment timeout service stopped")

async def check_payment_timeout(session: Session, order_id: int) -> bool:
    """Проверяет, не истекло ли время оплаты"""
    order = session.get(Order, order_id)
    if not order:
        return False
    
    if (order.status == OrderStatus.WAITING_PAYMENT and 
        order.payment_timeout_at and 
        order.payment_timeout_at <= datetime.now()):
        return True
    
    return False

def set_payment_timeout(session: Session, order: Order, timeout_minutes: int):
    """Устанавливает таймаут оплаты для заказа"""
    order.payment_timeout_at = datetime.now() + timedelta(minutes=timeout_minutes)
    order.updated_at = datetime.now()
    session.add(order)
    session.commit()