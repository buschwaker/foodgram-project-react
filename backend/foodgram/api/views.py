from io import StringIO

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from api import serializers
from api.filters import IngredientSearchCustom, RecipeFilterCustom
from api.mixins import CreateRetrieveListViewSet
from api.paginators import LimitPagePaginator
from api.permissions import AuthorAdminOrRead, IsAuthenticatedOrReadOnlyPost
from recipes import models
from users.models import Follow, User


class UserViewSet(CreateRetrieveListViewSet):
    lookup_field = 'id'
    queryset = User.objects.all()
    pagination_class = LimitPagePaginator
    permission_classes = (IsAuthenticatedOrReadOnlyPost, )

    def get_serializer_class(self):
        if self.action == 'set_password':
            return serializers.ChangePasswordSerializer
        elif not self.request.user.is_authenticated and (
                self.action == 'list'
                or self.action == 'retrieve'
                or self.action == 'create'
        ):
            return serializers.UserSerializerAnonymous
        return serializers.UserSerializer

    @action(detail=False,
            methods=['get'],
            permission_classes=[permissions.IsAuthenticated]
            )
    def me(self, request):
        serializer = self.get_serializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        url_name='set_password',
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def set_password(self, request):
        serializer = self.get_serializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=(permissions.IsAuthenticated, ))
    def subscriptions(self, request):
        following = self.get_queryset().filter(
            following__user=request.user
        ).order_by('pk')
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = serializers.SubscriptionsSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = serializers.SubscriptionsSerializer(
            following, many=True, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class IngredientsView(viewsets.ReadOnlyModelViewSet):
    queryset = models.Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
    filter_backends = (IngredientSearchCustom, )
    search_fields = ('$name', '^name', )


class TagsView(viewsets.ReadOnlyModelViewSet):
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer


class RecipeView(viewsets.ModelViewSet):
    queryset = models.Recipe.objects.all()
    pagination_class = LimitPagePaginator
    filter_backends = (RecipeFilterCustom, )
    permission_classes = (AuthorAdminOrRead, )

    def get_serializer_class(self):
        if not self.request.user.is_authenticated and (
                self.action == 'list' or self.action == 'retrieve'
        ):
            return serializers.RecipeSerializerAnonymous
        elif self.request.user.is_authenticated and (
                self.action == 'list' or self.action == 'retrieve'
        ):
            return serializers.RecipeSerializerGet
        return serializers.RecipeSerializer

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        cart_file = StringIO()
        ingredients = models.IngredientAmount.objects.filter(
            recipes__carts__user=request.user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            ingredient_amount=Sum('amount')
        ).values_list(
            'ingredient__name',
            'ingredient__measurement_unit',
            'ingredient_amount'
        )
        cart_file.write('Нужно купить: ')
        for ingredient in ingredients:
            cart_file.write(
                f'{ingredient[0]} {ingredient[2]} {ingredient[1]}, '
            )
        response = HttpResponse(
            cart_file.getvalue(),
            content_type='text'
        )
        response['Content-Disposition'] = ('attachment; '
                                           'filename="%s"' % 'cart_file.txt')
        return response


class CustomDeletePost(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    @staticmethod
    def custom_post(request, pk, serializer_param, kwargs):
        serializer = serializer_param(
            data=request.data, context={'pk': pk, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, **kwargs)
        return serializer.data

    @staticmethod
    def custom_delete(klass, request, kwargs):
        obj = get_object_or_404(klass, user=request.user, **kwargs)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavouriteView(CustomDeletePost):

    def post(self, request, recipe_id):
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        dict_to_return = self.custom_post(
            request, recipe_id,
            serializers.FavouriteSerializer, {'recipe': recipe}
        )
        del dict_to_return['user']
        return Response(dict_to_return, status=status.HTTP_201_CREATED)

    def delete(self, request, recipe_id):
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        return self.custom_delete(
            models.Favourite, request, {'recipe': recipe}
        )


class FollowView(CustomDeletePost):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request, user_id):
        user_to_follow = get_object_or_404(User, id=user_id)
        dict_to_return = self.custom_post(
            request, user_id,
            serializers.FollowSerializer, {'author': user_to_follow}
        )
        return Response(
            dict_to_return.pop('author'), status=status.HTTP_201_CREATED
        )

    def delete(self, request, user_id):
        user_to_unfollow = get_object_or_404(User, id=user_id)
        return self.custom_delete(
            Follow, request, {'author': user_to_unfollow}
        )


class CartView(CustomDeletePost):
    def post(self, request, recipe_id):
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        dict_to_return = self.custom_post(
            request, recipe_id, serializers.CartSerializer, {'recipe': recipe}
        )
        del dict_to_return['user']
        return Response(dict_to_return, status=status.HTTP_201_CREATED)

    def delete(self, request, recipe_id):
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        return self.custom_delete(models.Cart, request, {'recipe': recipe})
