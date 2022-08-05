from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from users.models import Follow, User


@admin.register(User)
class UserAdminCustom(UserAdmin):
    """Панель администратора для модели MyUser"""
    fieldsets = (
        (None, {'fields': ('username', 'password', 'is_staff')}),
        (_('Personal info'),
         {'fields': (
             'first_name', 'last_name', 'email'
         )}),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2',
                'email', 'first_name', 'last_name', 'is_staff'
            ),
        }),
    )
    list_filter = ('email', 'username')
    list_display = ('username', 'email', 'is_staff')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Управление жанрами админом."""
    list_display = (
        'user',
        'author',
    )
