from django.core.validators import MinValueValidator
from django.db import models

from users.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    measurement_unit = models.CharField(
        max_length=15, verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name_plural = 'Ингредиенты'
        verbose_name = 'Ингредиент'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=50, verbose_name='Название', unique=True
    )
    color = models.CharField(
        max_length=50, verbose_name='Hex цвет', unique=True
    )
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = 'Теги'
        verbose_name = 'Тег'

    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE
    )
    amount = models.FloatField(
        validators=[MinValueValidator(0), ]
    )

    def __str__(self):
        return f'{self.amount}|{self.ingredient}'


class Recipe(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Пользователь',
        related_name='recipes'
    )
    ingredients = models.ManyToManyField(
        IngredientAmount, verbose_name='Ингредиенты',
        blank=False, related_name='recipes'
    )
    tags = models.ManyToManyField(Tag, verbose_name='Теги', blank=False)
    image = models.ImageField(
        verbose_name='Изображение рецепта',
        upload_to='recipes/',
        help_text='Загрузите изображение рецепта'
    )
    name = models.CharField(max_length=200, verbose_name='Название')
    text = models.TextField(verbose_name='Описание')
    cooking_time = models.IntegerField(
        validators=[MinValueValidator(1), ],
        verbose_name='Время приготовления'
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )

    class Meta:
        verbose_name_plural = 'Рецепты'
        verbose_name = 'Рецепт'
        ordering = ['-pub_date']

    def __str__(self):
        return self.name


class Favourite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favourites',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='favourites',
    )

    class Meta:
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe'),
        ]
        verbose_name_plural = 'Избранные'
        verbose_name = 'Избранное'

    def __str__(self):
        return (f'{self.user.username} added'
                f' to favourites {self.recipe.name}')


class Cart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='carts',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='carts',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='cart_unique_user_recipe'),
        ]
        ordering = ['user']
        verbose_name_plural = 'Покупки'
        verbose_name = 'Покупка'

    def __str__(self):
        return f'{self.user.username} gonna buy: {self.recipe.name}'
