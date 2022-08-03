import csv

from recipes.models import Ingredient


def create_ingredients():
    """Создание dummy data для ингредиентов из csv файла"""
    with open('data/ingredients.csv', encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            Ingredient.objects.create(
                name=row.get('абрикосовое варенье'),
                measurement_unit=row.get('г'),
            )
