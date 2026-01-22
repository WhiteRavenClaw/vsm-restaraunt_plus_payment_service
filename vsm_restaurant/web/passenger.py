from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import func, select

from vsm_restaurant.db.cooking_task import CookingStatus, CookingTask
from vsm_restaurant.db.menu import MenuItemModel
from vsm_restaurant.db.orders import Order, OrderItem, OrderStatus
from vsm_restaurant.dependencies import SessionDep
from vsm_restaurant.schemas.orders import OrderItemOut
from vsm_restaurant.schemas.passenger import (
    OrderStatusResponse,
    PassengerOrderHistory,
    PassengerOrderStatus,
)
from vsm_restaurant.services.availability import check_menu_item_availability
from vsm_restaurant.services.estimation import estimate_completion_time

router = APIRouter()
templates = Jinja2Templates(directory="vsm_restaurant/web/templates")


@router.get("/passenger", response_class=HTMLResponse)
async def passenger_page(request: Request):
    return templates.TemplateResponse("passenger.html", {"request": request})


@router.get("/passenger/order/{order_id}", response_model=OrderStatusResponse)
def get_order_status(order_id: int, session: SessionDep):
    order = session.get(Order, order_id)
    if not order:
        return OrderStatusResponse(
            success=False,
            message="Order not found",
        )

    items_with_details = []
    for item in order.items:
        menu_item = session.get(MenuItemModel, item.menu_item_id)
        items_with_details.append(
            OrderItemOut(
                id=item.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                menu_item=menu_item,
            )
        )

    estimated_time = estimate_completion_time(session, order_id)

    order_status = PassengerOrderStatus(
        order_id=order.id,
        place_id=order.place_id,
        status=order.status,
        total_price=order.total_price,
        created_at=order.created_at,
        estimated_time=estimated_time,
        items=items_with_details,
    )

    return OrderStatusResponse(
        success=True,
        order=order_status,
        message=f"Order {order_id} status: {order.status.value}",
    )


@router.get("/passenger/orders/{place_id}", response_model=List[PassengerOrderHistory])
def get_order_history(place_id: str, session: SessionDep, limit: int = 10):
    orders = session.exec(
        select(Order)
        .where(Order.place_id == place_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()

    history = []
    for order in orders:
        item_count = session.exec(
            select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
        ).first()

        history.append(
            PassengerOrderHistory(
                order_id=order.id,
                status=order.status,
                total_price=order.total_price,
                created_at=order.created_at,
                item_count=item_count or 0,
            )
        )

    return history


@router.post("/passenger/order/{order_id}/cancel")
def cancel_order(order_id: int, session: SessionDep):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    cancellable_statuses = [OrderStatus.WAITING_PAYMENT, OrderStatus.PAID]

    if order.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order in status: {order.status.value}",
        )

    cooking_tasks = session.exec(
        select(CookingTask)
        .where(CookingTask.order_id == order_id)
        .where(CookingTask.status != CookingStatus.QUEUED)
    ).first()

    if cooking_tasks:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel order - cooking already started",
        )

    order.status = OrderStatus.CANCELLED

    if order.payment_method == "card_online" and order.status == OrderStatus.PAID:
        print(f"Refund initiated for order {order_id}")

    session.commit()

    return {
        "success": True,
        "message": f"Order {order_id} cancelled successfully",
        "refund_initiated": order.payment_method == "card_online",
    }


@router.get("/passenger/menu/available")
def get_available_menu(session: SessionDep):
    all_menu_items = session.exec(select(MenuItemModel)).all()

    available_items = []
    for item in all_menu_items:
        if check_menu_item_availability(session, item.id):
            available_items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "price": float(item.price),
                    "composition": item.composition,
                }
            )

    return {
        "available_items": available_items,
        "total_available": len(available_items),
        "timestamp": "2024-01-01T00:00:00Z",
    }
