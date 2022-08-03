from django.urls import include, path
from rest_framework import routers
from djoser.views import TokenCreateView, TokenDestroyView


from .views import (UserViewSet, IngredientsView, TagsView, RecipeView,
                    FavouriteView, FollowView, CartView)

app_name = 'api'


class NoPutRouter(routers.DefaultRouter):
    """
    Класс роутер, отключающий PUT запросы
    """
    def get_method_map(self, viewset, method_map):

        bound_methods = super().get_method_map(viewset, method_map)

        if 'put' in bound_methods.keys():
            del bound_methods['put']

        return bound_methods


router_v1 = NoPutRouter()

router_v1.register('users', UserViewSet, basename='user')
router_v1.register('ingredients', IngredientsView, basename='ingredient')
router_v1.register('tags', TagsView, basename='tag')
router_v1.register('recipes', RecipeView, basename='recipe')


urlpatterns = [
    path('', include(router_v1.urls)),
    path(
        'auth/token/login/',
        TokenCreateView.as_view(),
        name='token_obtain_pair'
    ),
    path(
        'auth/token/logout/',
        TokenDestroyView.as_view(),
        name='token_delete_pair'
    ),
    path(
        'recipes/<int:recipe_id>/favorite/',
        FavouriteView.as_view(),
        name='add_delete_favourites'
    ),
    path(
        'recipes/<int:recipe_id>/shopping_cart/',
        CartView.as_view(),
        name='add_delete_recipes_from_cart'
    ),
    path(
        'users/<int:user_id>/subscribe/',
        FollowView.as_view(),
        name='add_delete_subscriptions'
    )
]
