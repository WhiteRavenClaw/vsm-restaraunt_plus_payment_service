from fastapi import APIRouter, Depends
from sqlmodel import select
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.db.order import Order

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/")
def list_orders(session: SessionDep):
    return session.exec(select(Order)).all()

@router.post("/")
def create_order(order: Order, session: SessionDep):
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
