from fastapi import APIRouter, Depends
from sqlmodel import select
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.orders import Order, OrderItem

router = APIRouter()

@router.get("/orders")
def list_orders(session: SessionDep):
    return session.exec(select(Order)).all()

@router.post("/orders")
def create_order(order: Order, session: SessionDep):
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
