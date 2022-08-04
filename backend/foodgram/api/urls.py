from api import views
from django.urls import include, path
from djoser.views import TokenCreateView, TokenDestroyView
from rest_framework import routers

app_name = 'api'


class NoPutRouter(routers.DefaultRouter):
    """
    Класс роутер, отключающий PUT запросы
    """
    def get_method_map(self, viewset, method_map):

        bound_methods = super().get_method_map(viewset, method_map)

        if 'put' in bound_methods:
            del bound_methods['put']

        return bound_methods


router_v1 = NoPutRouter()

router_v1.register('users', views.UserViewSet, basename='user')
router_v1.register('ingredients', views.IngredientsView, basename='ingredient')
router_v1.register('tags', views.TagsView, basename='tag')
router_v1.register('recipes', views.RecipeView, basename='recipe')


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
        views.FavouriteView.as_view(),
        name='add_delete_favourites'
    ),
    path(
        'recipes/<int:recipe_id>/shopping_cart/',
        views.CartView.as_view(),
        name='add_delete_recipes_from_cart'
    ),
    path(
        'users/<int:user_id>/subscribe/',
        views.FollowView.as_view(),
        name='add_delete_subscriptions'
    )
]
