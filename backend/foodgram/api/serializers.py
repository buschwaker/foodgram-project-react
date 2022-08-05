from django.contrib.auth.password_validation import validate_password
from django.shortcuts import Http404, get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes import models
from users.models import Follow, MyUser


class UserSerializer(serializers.ModelSerializer):
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

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError(
                'Старый пароль введен некорректно'
            )

    def validate_new_password(self, value):
        validate_password(value)
        return value


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Ingredient
        fields = '__all__'


class TagSerializer(IngredientSerializer):

    class Meta(IngredientSerializer.Meta):
        model = models.Tag
        fields = ('id', 'name', 'color', 'slug')
        read_only_fields = ('name', 'color', 'slug')


class IngredientWithAmountSerializer(serializers.ModelSerializer):
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name', read_only=True)

    class Meta:
        model = models.IngredientAmount
        fields = ('id', 'amount', 'name', 'measurement_unit')


class AuthorSerialiser(serializers.ModelSerializer):
    class Meta:
        model = models.Recipe
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
        model = models.Recipe
        fields = (
            'id', 'tags', 'ingredients',
            'image', 'name', 'text', 'cooking_time', 'author'
        )


class RecipeSerializerGet(serializers.ModelSerializer):
    ingredients = IngredientWithAmountSerializer(many=True, required=True)
    tags = TagSerializer(many=True, required=True)
    author = UserSerializer(many=False, read_only=True)
    image = Base64ImageField(max_length=None, use_url=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def get_is_in_shopping_cart(self, obj):
        return models.Cart.objects.filter(
            user=self.context['request'].user, recipe=obj
        ).exists()

    def get_is_favorited(self, obj):
        return models.Favourite.objects.filter(
            user=self.context['request'].user, recipe=obj
        ).exists()

    class Meta:
        model = models.Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'image',
            'is_favorited', 'name', 'text', 'cooking_time',
            'is_in_shopping_cart'
        )


class RecipeSerializer(RecipeSerializerGet):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=models.Tag.objects.all(),
        many=True
    )

    def validate(self, data):
        for data_ingredient in data['ingredients']:
            try:
                get_object_or_404(
                    models.Ingredient, pk=data_ingredient['ingredient']['id']
                )
            except Http404:
                raise serializers.ValidationError(
                    f'Нет ингредиента'
                    f' id = {data_ingredient["ingredient"]["id"]}'
                )
        if len(data['tags']) == 0:
            raise serializers.ValidationError(
                'Рецепт должен включать хотя бы 1 тег'
            )
        return data

    def get_data_for_post_and_update(self):
        validated_ingredients = self.validated_data.get('ingredients')
        ingredients_list = []
        if validated_ingredients:
            for ingredient in validated_ingredients:
                ing_id = models.Ingredient.objects.get(
                    pk=ingredient['ingredient']['id']
                )
                try:
                    ingredient_recipe = get_object_or_404(
                        models.IngredientAmount,
                        ingredient=ing_id,
                        amount=ingredient['amount']
                    )
                except Http404:
                    ingredient_recipe = models.IngredientAmount.objects.create(
                        ingredient=ing_id, amount=ingredient['amount']
                    )
                ingredients_list.append(ingredient_recipe)
        return ingredients_list or None

    def create(self, validated_data):

        ingredients = self.get_data_for_post_and_update()
        tags = validated_data.pop('tags')
        validated_data.pop('ingredients')
        validated_data.update({'author': self.context['request'].user})
        recipe = models.Recipe.objects.create(**validated_data)
        recipe.ingredients.set(ingredients)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        ingredients = self.get_data_for_post_and_update()
        tags = validated_data.pop('tags')
        validated_data.pop('ingredients')
        validated_data.update({'author': self.context['request'].user})
        instance.tags.set(tags or instance.tags)
        instance.ingredients.set(ingredients or instance.ingredients)
        instance.save()
        return super(RecipeSerializer, self).update(instance, validated_data)

    class Meta:
        model = models.Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'image',
            'is_favorited', 'name', 'text', 'cooking_time',
            'is_in_shopping_cart'
        )


class SubscriptionRecipesSerializer(serializers.ModelSerializer):
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = models.Recipe
        fields = ('id', 'name', 'cooking_time', 'image')


class SubscriptionsSerializer(UserSerializer):
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
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True
    )

    def custom_validation(self, klass, attrs):
        if klass.objects.filter(
                user=self.context['request'].user, recipe=self.context['pk']
        ).exists():
            raise serializers.ValidationError(
                'Нельзя дважды один и тот же '
                'рецепт добавить в избранное или в покупки'
            )
        return attrs

    def validate(self, attrs):
        self.custom_validation(models.Favourite, attrs)
        return attrs

    class Meta:
        model = models.Favourite
        fields = ('id', 'user', 'cooking_time', 'name', 'image')


class CartSerializer(FavouriteSerializer):

    def validate(self, attrs):
        self.custom_validation(models.Cart, attrs)
        return attrs

    class Meta:
        model = models.Cart
        fields = ('id', 'user', 'cooking_time', 'name', 'image')


class FollowSerializer(serializers.ModelSerializer):
    author = SubscriptionsSerializer(read_only=True)
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )

    def validate(self, attrs):
        if self.context['request'].user.pk == self.context['pk']:
            raise serializers.ValidationError(
                'Нельзя подписаться на себя!'
            )
        if Follow.objects.filter(
                user=self.context['request'].user,
                author=MyUser.objects.get(pk=self.context['pk'])
        ).exists():
            raise serializers.ValidationError(
                "Нельзя дважды подписаться на одного и того же пользователя"
            )
        if not MyUser.objects.filter(pk=self.context['pk']).exists():
            raise serializers.ValidationError('Нет юзера с таким id!')
        return attrs

    class Meta:
        model = Follow
        fields = '__all__'
