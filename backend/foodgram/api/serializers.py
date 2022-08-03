from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404, Http404

from drf_extra_fields.fields import Base64ImageField

from rest_framework import serializers

from users.models import Follow, MyUser
from recipes.models import (
    Ingredient, Tag, Recipe, IngredientAmount, Favourite, Cart
)


class MyUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    def create(self, validated_data):
        user = super().create(validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(
            user=self.context['request'].user, author=obj
        ).exists()

    class Meta:
        model = MyUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'password'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True},
        }


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(IngredientSerializer):

    class Meta(IngredientSerializer.Meta):
        model = Tag
        fields = ('id', 'name', 'color', 'slug')
        read_only_fields = ('name', 'color', 'slug')


class IngredientWithAmountSerializer(serializers.ModelSerializer):
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name', read_only=True)

    class Meta:
        model = IngredientAmount
        fields = ('id', 'amount', 'name', 'measurement_unit')


class AuthorSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('email', 'id', 'username', 'first_name', 'last_name')


class UserSerializerAnonymous(serializers.ModelSerializer):
    def create(self, validated_data):
        user = super().create(validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    class Meta:
        model = MyUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'password'
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }


class RecipeSerializerAnonymous(serializers.ModelSerializer):
    ingredients = IngredientWithAmountSerializer(many=True, required=True)
    tags = TagSerializer(many=True, required=True)
    author = UserSerializerAnonymous(many=False, read_only=True)
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'ingredients',
            'image', 'name', 'text', 'cooking_time', 'author'
        )


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientWithAmountSerializer(many=True, required=True)
    tags = TagSerializer(many=True, required=True)
    author = MyUserSerializer(many=False, read_only=True)
    image = Base64ImageField(max_length=None, use_url=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def get_is_in_shopping_cart(self, obj):
        return Cart.objects.filter(
            user=self.context['request'].user, recipe=obj
        ).exists()

    def get_is_favorited(self, obj):
        return Favourite.objects.filter(
            user=self.context['request'].user, recipe=obj
        ).exists()

    def to_internal_value(self, data):
        if data.get('tags') is not None and all(
                isinstance(x, int) for x in data.get('tags')
        ):
            list_to_return = []
            tags = data.pop('tags')
            for tag in tags:
                list_to_return.append({'id': tag})
            data.update({'tags': list_to_return})
        return super().to_internal_value(data)

    def get_data_for_post_and_update(self):
        initial_tags = self.initial_data.pop('tags', None)
        initial_ingredients = self.initial_data.pop('ingredients', None)
        tags_list = []
        ingredients_list = []
        if initial_tags or None:
            for tag in initial_tags:
                try:
                    tag_to_recipe = get_object_or_404(Tag, pk=tag['id'])
                except Http404:
                    raise serializers.ValidationError(
                        f'Нет тэга id = {tag["id"]}'
                    )
                tags_list.append(tag_to_recipe)
        if initial_ingredients:
            for ingredient in initial_ingredients:
                try:
                    ing = get_object_or_404(Ingredient, pk=ingredient['id'])
                except Http404:
                    raise serializers.ValidationError(
                        f'Нет ингредиента id = {ingredient["id"]}'
                    )
                try:
                    ingredient_recipe = get_object_or_404(
                        IngredientAmount,
                        ingredient=ing,
                        amount=ingredient['amount']
                    )
                except Http404:
                    ingredient_recipe = IngredientAmount.objects.create(
                        ingredient=ing, amount=ingredient['amount']
                    )
                ingredients_list.append(ingredient_recipe)
        tags_list = tags_list or None
        ingredients_list = ingredients_list or None
        return tags_list, ingredients_list

    def create(self, validated_data):
        tags, ingredients = self.get_data_for_post_and_update()
        if not tags or not ingredients:
            raise serializers.ValidationError(
                'Поле теги или ингридиенты пустое!'
            )
        recipe = Recipe.objects.create(
            name=validated_data['name'],
            text=validated_data['text'],
            cooking_time=validated_data['cooking_time'],
            author=self.context['request'].user,
            image=validated_data['image']
        )
        recipe.tags.set(tags)
        recipe.ingredients.set(ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags, ingredients = self.get_data_for_post_and_update()
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.tags.set(tags or instance.tags)
        instance.ingredients.set(ingredients or instance.ingredients)
        instance.save()
        return instance

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'image',
            'is_favorited', 'name', 'text', 'cooking_time',
            'is_in_shopping_cart'
        )


class SubscriptionRecipesSerializer(serializers.ModelSerializer):
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'cooking_time', 'image')


class SubscriptionsSerializer(MyUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'recipes',
            'recipes_count', 'is_subscribed'
        )

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        recipes_limit = (
            self.context['request'].query_params.get('recipes_limit')
        )
        recipes = obj.recipes.all()
        if recipes_limit is not None:
            recipes_limit = int(recipes_limit)
            serializer = SubscriptionRecipesSerializer(
                recipes[:recipes_limit], many=True
            )
        else:
            serializer = SubscriptionRecipesSerializer(recipes, many=True)
        return serializer.data


class FavouriteSerializer(serializers.ModelSerializer):
    name = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True,
        source='recipe'
    )
    image = serializers.ImageField(source='recipe.image', read_only=True)
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    cooking_time = serializers.SerializerMethodField()

    class Meta:
        model = Favourite
        fields = ('id', 'user', 'cooking_time', 'name', 'image')

    def get_cooking_time(self, obj):
        return obj.recipe.cooking_time


class CartSerializer(FavouriteSerializer):
    class Meta:
        model = Cart
        fields = ('id', 'user', 'cooking_time', 'name', 'image')


class FollowSerializer(serializers.ModelSerializer):
    author = SubscriptionsSerializer(read_only=True)
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )

    class Meta:
        model = Follow
        fields = '__all__'
