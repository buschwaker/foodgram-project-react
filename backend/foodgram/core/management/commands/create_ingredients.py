from django.core.management.base import BaseCommand
from core.csv_reader import create_ingredients


class Command(BaseCommand):

    help = 'Команда создающая dummy data для модели Ingredients'

    def handle(self, *args, **kwargs):
        create_ingredients()
