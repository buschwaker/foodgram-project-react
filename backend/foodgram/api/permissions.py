from rest_framework import permissions


class AuthorAdminOrRead(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.user and request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        elif obj.author == request.user or request.user.is_staff:
            return True
        return False


class IsAuthenticatedOrReadOnlyPost(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.method == 'POST' or request.user
            and request.user.is_authenticated
        )
