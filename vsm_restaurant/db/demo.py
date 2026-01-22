from datetime import datetime
from enum import Enum

from pydantic import ConfigDict
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, VARCHAR
from sqlalchemy.sql.schema import Index
from sqlmodel import Field, SQLModel


class DemoEnumType(int, Enum):
    NONE = 0
    VARIANT_1 = 1
    VARIANT_2 = 2


class DemoModel(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    timestamp: datetime = Field()
    title: str | None = Field(sa_column=Column(VARCHAR(255)))
    message: str | None = Field(sa_column=Column(TEXT), default=None)
    demo_enum: DemoEnumType | None = Field(sa_column=Column(INTEGER), default=None)
    json_data: dict | None = Field(sa_column=Column(JSONB), default=None)

    __tablename__ = "demo"
    __table_args__ = (
        Index(
            "demo_timestamp_idx",
            "timestamp",
            unique=False
        ),
    )

    model_config = ConfigDict(use_enum_values=True)

    def demo_enum_name(self):
        if self.demo_enum is None:
            return None
        return DemoEnumType(self.demo_enum).name
