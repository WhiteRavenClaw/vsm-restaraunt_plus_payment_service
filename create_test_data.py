from sqlmodel import create_engine, Session
from vsm_restaurant.db.menu import IngredientModel, MenuItemModel
from vsm_restaurant.settings import Settings

def create_test_data():
    settings = Settings()
    engine = create_engine(settings.db_url)
    
    with Session(engine) as session:
        # Создаем ингредиенты
        ingredients = [
            IngredientModel(name="Хлеб", stock=100),
            IngredientModel(name="Сыр", stock=50),
            IngredientModel(name="Ветчина", stock=30),
            IngredientModel(name="Помидор", stock=40),
            IngredientModel(name="Салат", stock=25),
            IngredientModel(name="Кофе", stock=100),
            IngredientModel(name="Молоко", stock=60),
        ]
        
        for ingredient in ingredients:
            session.add(ingredient)
        
        session.commit()
        
        # Создаем позиции меню
        menu_items = [
            MenuItemModel(
                name="Сэндвич с ветчиной",
                price=250.0,
                composition=[
                    {"ingredient_id": 1, "quantity": 2},
                    {"ingredient_id": 2, "quantity": 1},
                    {"ingredient_id": 3, "quantity": 1},
                    {"ingredient_id": 5, "quantity": 1}
                ]
            ),
            MenuItemModel(
                name="Кофе латте",
                price=180.0,
                composition=[
                    {"ingredient_id": 6, "quantity": 1},
                    {"ingredient_id": 7, "quantity": 1}
                ]
            ),
            MenuItemModel(
                name="Сэндвич вегетарианский",
                price=200.0,
                composition=[
                    {"ingredient_id": 1, "quantity": 2},
                    {"ingredient_id": 2, "quantity": 1},
                    {"ingredient_id": 4, "quantity": 1},
                    {"ingredient_id": 5, "quantity": 1}
                ]
            ),
        ]
        
        for item in menu_items:
            session.add(item)
        
        session.commit()
        print("Test data created successfully!")

if __name__ == "__main__":
    create_test_data()