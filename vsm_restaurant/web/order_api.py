from fastapi import APIRouter, Depends
from sqlmodel import select, Session
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem,OrderStatus,PaymentMethod
from vsm_restaurant.db.cooking_task import CookingTask, CookingStatus
from vsm_restaurant.db.menu import MenuItemModel
router = APIRouter()

@router.get("/orders")
def list_orders(session: SessionDep):
    return session.exec(select(Order)).all()

@router.post("/orders")
# def create_order(order: Order, session: SessionDep):
#     session.add(order)
#     session.commit()
#     session.refresh(order)
#     return order
def create_order(order_data: Order, session: SessionDep):
    order = Order(
        seat_number=order_data.place_id,
        trans_id=order_data.trans_id,
        payment_method=order_data.payment_method,
        status=order_data.status,
        total_price=order_data.total_price,
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    # Создаём задачи на готовку, если заказ нужно готовить сразу
    if order.status in [OrderStatus.PAID, OrderStatus.COOKING] or order.payment_method in [
        PaymentMethod.CARD_TERMINAL,
        PaymentMethod.CASH,
    ]:
        for item in order_data.items:  # предполагается, что есть список блюд
            task = CookingTask(
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                status=CookingStatus.QUEUED
            )
            session.add(task)
        session.commit()

    return order