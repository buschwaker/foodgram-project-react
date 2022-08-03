from rest_framework import filters


class RecipeFilterCustom(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        tags = request.query_params.getlist('tags')
        if len(tags) != 0:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        author = request.query_params.get('author')
        if author is not None:
            queryset = queryset.filter(author__id=author)
        if request.query_params.get('is_favorited'):
            queryset = queryset.filter(
                id__in=request.user.favourites.values('recipe')
            ).distinct()
        if request.query_params.get('is_in_shopping_cart'):
            queryset = queryset.filter(
                id__in=request.user.carts.values('recipe')
            ).distinct()
        return queryset


class IngredientSearchCustom(filters.SearchFilter):
    search_param = 'name'
