from sqlmodel import Session, select
from ..db.menu import MenuItemModel, IngredientModel

def check_menu_item_availability(session: Session, menu_item_id: int) -> bool:
    menu_item = session.get(MenuItemModel, menu_item_id)
    if not menu_item or not menu_item.composition:
        return False
    
    for ingredient_req in menu_item.composition:
        ingredient = session.get(IngredientModel, ingredient_req["ingredient_id"])
        if not ingredient or ingredient.stock < ingredient_req["quantity"]:
            return False
    
    return True

def reserve_ingredients(session: Session, menu_item_id: int):
    menu_item = session.get(MenuItemModel, menu_item_id)
    if not menu_item.composition:
        return
    
    for ingredient_req in menu_item.composition:
        ingredient = session.get(IngredientModel, ingredient_req["ingredient_id"])
        if ingredient:
            ingredient.stock -= ingredient_req["quantity"]
            session.add(ingredient)