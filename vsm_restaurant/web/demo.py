from datetime import timedelta, datetime

from fastapi import APIRouter
from sqlmodel import select, desc

from vsm_restaurant.db import DemoModel
from vsm_restaurant.db.demo import DemoEnumType
from vsm_restaurant.dependencies import SessionDep

router = APIRouter()


# In real code you'd probably use DTOs instead of SQLModel models for requests and responses.
# So that you can map and validate enums, for example.

@router.get("/demo/recent")
async def list_demos(session: SessionDep, limit: int = 100, days: int = 7):
    demos = session.exec(
        select(DemoModel).where(DemoModel.timestamp > datetime.now() - timedelta(days=days))
        .order_by(desc(DemoModel.timestamp))
        .limit(limit)
    )
    return list(demos)


@router.post("/demo/create")
async def list_demos(session: SessionDep, model: DemoModel):
    if model.timestamp is None:
        model.timestamp = datetime.now()
    if type(model.demo_enum) is str:
        model.demo_enum = DemoEnumType[model.demo_enum]
    session.add(model)
    session.commit()
    # Commit clears the model state, so we need to refresh it
    session.refresh(model)
    return model
