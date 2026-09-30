"""Pagination contract.

`docs/04-api-specification.md` section 4 requires `?page=`/`?page_size=` and a
response shape that stays consistent across the API. Fixing one shared class
now prevents per-endpoint drift later.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
