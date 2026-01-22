from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from sqlmodel import select

from vsm_restaurant.db.cooking_task import CookingStatus, CookingTask
from vsm_restaurant.dependencies import SessionDep

router = APIRouter()


class CookingTaskCreate(BaseModel):
    order_id: int
    menu_item_id: int


class CookingTaskUpdate(BaseModel):
    status: CookingStatus


@router.get("/tasks")
def list_tasks(session: SessionDep):
    return session.exec(select(CookingTask)).all()


@router.post("/tasks")
def create_task(task_data: CookingTaskCreate, session: SessionDep):
    task = CookingTask(
        order_id=task_data.order_id,
        menu_item_id=task_data.menu_item_id,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.patch("/tasks/{task_id}")
def update_task_status(task_id: int, update: CookingTaskUpdate, session: SessionDep):
    task = session.get(CookingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = update.status
    session.commit()
    session.refresh(task)
    return task
