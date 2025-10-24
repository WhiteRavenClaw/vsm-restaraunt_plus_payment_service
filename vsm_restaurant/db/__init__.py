import alembic.command
import alembic.config
from sqlalchemy import Engine
from sqlmodel import create_engine

from ..settings import Settings

# Remember to import your models here for alembic to discover them
from .demo import DemoModel
from .menu import IngredientModel, MenuItemModel, MenuItemCreate, IngredientCreate, IngredientUpdate


def run_migrations(settings: Settings):
    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.db_url)
    alembic.command.upgrade(alembic_cfg, "head")

def create_db_engine(settings: Settings) -> Engine:
    return create_engine(settings.db_url)
