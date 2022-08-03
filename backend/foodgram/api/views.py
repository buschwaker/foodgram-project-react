from io import StringIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, Http404

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from api.paginators import LimitPagePaginator
from api.mixins import CreateRetrieveListViewSet
from users.models import MyUser, Follow
from recipes.models import (
    Ingredient, Tag, Recipe, Favourite, Cart, IngredientAmount
)
from .serializers import (
    MyUserSerializer, ChangePasswordSerializer, IngredientSerializer,
    TagSerializer, RecipeSerializer, FavouriteSerializer,
    SubscriptionsSerializer, CartSerializer, RecipeSerializerAnonymous,
    UserSerializerAnonymous, FollowSerializer
)
from .filters import RecipeFilterCustom, IngredientSearchCustom
from .permissions import (
    AuthorAdminOrReadOnly, IsAuthenticatedOrReadOnlyOrPost
)


class UserViewSet(CreateRetrieveListViewSet):
    lookup_field = 'id'
    queryset = MyUser.objects.all()
    pagination_class = LimitPagePaginator
    permission_classes = (IsAuthenticatedOrReadOnlyOrPost, )

    def get_serializer_class(self):
        if self.action == 'set_password':
            return ChangePasswordSerializer
        elif not self.request.user.is_authenticated and (
                self.action == 'list'
                or self.action == 'retrieve'
                or self.action == 'create'
        ):
            return UserSerializerAnonymous
        return MyUserSerializer

    def get_me(self):
        return MyUser.objects.get(username=self.request.user.username)

    @action(detail=False,
            methods=['get'],
            permission_classes=[permissions.IsAuthenticated]
            )
    def me(self, request):
        me = self.get_me()
        serializer = self.get_serializer(me, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=False,
        url_name='set_password',
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def set_password(self, request):
        me = self.get_me()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            old_password = serializer.data.get("current_password")
            if not me.check_password(old_password):
                return Response(
                    {"current_password": ["Неправильный пароль!"]},
                    status=status.HTTP_400_BAD_REQUEST)
            me.set_password(serializer.data.get("new_password"))
            me.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, permission_classes=(permissions.IsAuthenticated, ))
    def subscriptions(self, request):
        following = self.get_queryset().filter(
            following__user=request.user
        ).order_by('pk')
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = SubscriptionsSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionsSerializer(
            following, many=True, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class IngredientsView(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientSearchCustom, )
    search_fields = ('name', )


class TagsView(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeView(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = LimitPagePaginator
    filter_backends = (RecipeFilterCustom, )
    # serializer_class = RecipeSerializer
    permission_classes = (AuthorAdminOrReadOnly, )

    def get_serializer_class(self):
        if not self.request.user.is_authenticated and (
                self.action == 'list' or self.action == 'retrieve'
        ):
            return RecipeSerializerAnonymous
        return RecipeSerializer

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        cart_file = StringIO()
        me = MyUser.objects.get(username=self.request.user.username)
        seen = {}
        for i in Recipe.objects.filter(
                id__in=me.carts.values('recipe')).values('ingredients'):
            id_ingredient = i['ingredients']
            if id_ingredient in seen:
                to_add = seen[id_ingredient]
                seen[id_ingredient] = to_add + 1
            else:
                seen[id_ingredient] = 1
        for i, repeats in seen.items():
            name = IngredientAmount.objects.get(id=i).ingredient.name
            amount = IngredientAmount.objects.get(id=i).amount * repeats
            measure_unit = IngredientAmount.objects.get(
                id=i
            ).ingredient.measurement_unit
            cart_file.write(f'{name} {amount } {measure_unit}, ')
        response = HttpResponse(
            cart_file.getvalue(),
            content_type='text'
        )
        response['Content-Disposition'] = ('attachment; '
                                           'filename="%s"' % 'cart_file.txt')
        return response


class FavouriteView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request, recipe_id):
        serializer = FavouriteSerializer(data=request.data)
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if serializer.is_valid():
            if Favourite.objects.filter(
                    user=self.request.user, recipe=recipe
            ).exists():
                return Response(
                    {
                        "errors":
                            "Нельзя дважды подписаться на один и тот же рецепт"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(user=self.request.user, recipe=recipe)
            dict_to_return = serializer.data
            del dict_to_return['user']
            return Response(dict_to_return, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, recipe_id):
        try:
            recipe = get_object_or_404(Recipe, id=recipe_id)
        except Http404:
            return Response(
                {"errors": "Для рецепта нет такого id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            favour = get_object_or_404(
                Favourite, user=self.request.user, recipe=recipe
            )
        except Http404:
            return Response(
                {
                    "errors":
                        f"Для пользователя "
                        f"{self.request.user} нет {recipe} в избранном"
                }, status=status.HTTP_400_BAD_REQUEST
            )
        favour.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request, user_id):
        serializer = FollowSerializer(
            data=request.data,
            context={'request': request}
        )
        user_to_follow = get_object_or_404(MyUser, id=user_id)
        if serializer.is_valid():
            if self.request.user == user_to_follow:
                return Response(
                    {"errors": "Нельзя подписаться на самого себя"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(
                    user=self.request.user, author=user_to_follow
            ).exists():
                return Response(
                    {
                        "errors":
                            "Нельзя дважды подписаться"
                            " на одного и того же пользователя"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(user=self.request.user, author=user_to_follow)
            return Response(
                serializer.data.pop('author'),
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, user_id):
        try:
            user_to_unfollow = get_object_or_404(MyUser, id=user_id)
        except Http404:
            return Response(
                {"errors": "Нет юзера с таким id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            sub = get_object_or_404(
                Follow, user=self.request.user,
                author=user_to_unfollow
            )
        except Http404:
            return Response(
                {
                    "errors":
                        f"Для пользователя "
                        f"{self.request.user} "
                        f"нет {user_to_unfollow} в подписках"
                }, status=status.HTTP_400_BAD_REQUEST
            )
        sub.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated, ]

    def post(self, request, recipe_id):
        serializer = CartSerializer(data=request.data)
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if serializer.is_valid():
            if Cart.objects.filter(
                    user=self.request.user, recipe=recipe
            ).exists():
                return Response(
                    {"errors": "Нельзя дважды добавить один и тот же рецепт"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(user=self.request.user, recipe=recipe)
            dict_to_return = serializer.data
            del dict_to_return['user']
            return Response(dict_to_return, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, recipe_id):
        try:
            recipe = get_object_or_404(Recipe, id=recipe_id)
        except Http404:
            return Response(
                {"errors": "Для рецепта нет такого id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            favour = get_object_or_404(
                Cart, user=self.request.user, recipe=recipe
            )
        except Http404:
            return Response(
                {
                    "errors":
                        f"Для пользователя "
                        f"{self.request.user} нет {recipe} в избранном"
                }, status=status.HTTP_400_BAD_REQUEST
            )
        favour.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
