from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class MyUser(AbstractUser):
    """Модель MyUser.
    При аутентификации в качестве логина используется email.
    """
    email = models.EmailField(
        _('email address'),
        blank=False,
        null=False,
        max_length=254,
        unique=True
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=False)
    last_name = models.CharField(_('last name'), max_length=150, blank=False)
    password = models.CharField(_('password'), max_length=150)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']


class Follow(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'),
        ]
        verbose_name_plural = 'Подписки'
        verbose_name = 'Подписка'

    def __str__(self):
        return f'{self.user.username} to {self.author.username}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на себя!')
