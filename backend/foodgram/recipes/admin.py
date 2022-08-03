from django.conf import settings
from django.contrib import admin

from .models import Ingredient, Tag, Recipe, IngredientAmount, Favourite, Cart


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
    )
    list_filter = ('name',)
    empty_value_display = settings.EMPTY_VALUE_DISPLAY


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'color',
    )
    search_fields = (
        'name',
    )
    list_filter = ('name',)
    empty_value_display = settings.EMPTY_VALUE_DISPLAY


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
    )
    readonly_fields = ('favorite_amount',)
    search_fields = (
        'name',
    )
    list_filter = ('name', 'author', 'tags')

    def favorite_amount(self, obj):
        return obj.favourites.count()

    empty_value_display = settings.EMPTY_VALUE_DISPLAY


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )


@admin.register(IngredientAmount)
class IngredientAmountAdmin(admin.ModelAdmin):
    list_display = (
        'ingredient',
        'amount',
    )
