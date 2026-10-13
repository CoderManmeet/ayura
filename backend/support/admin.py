from django.contrib import admin

from support.models import Query, QueryMessage, QueryPhoto


class QueryPhotoInline(admin.TabularInline):
    model = QueryPhoto
    extra = 0
    fields = ["image", "created_at"]
    readonly_fields = ["created_at"]


class QueryMessageInline(admin.TabularInline):
    """Messages are append-only, so the Django admin shows them and never edits them."""

    model = QueryMessage
    extra = 0
    fields = ["author", "body", "author_user", "created_at"]
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    """
    The owner's real screen for this is Admin area -> Support; this is the fallback.

    Status is editable here for repair work only. Changing it from here is NOT audited as an
    owner reply, so the admin area is the right place for ordinary work.
    """

    list_display = ["ref", "subject", "status", "owner_unread", "email", "order", "last_message_at"]
    list_filter = ["status", "owner_unread", "customer_unread"]
    search_fields = ["ref", "subject", "email", "phone_e164", "order__oid"]
    readonly_fields = ["ref", "created_at", "updated_at", "last_message_at"]
    autocomplete_fields = ["user"]
    date_hierarchy = "created_at"
    inlines = [QueryMessageInline]


@admin.register(QueryMessage)
class QueryMessageAdmin(admin.ModelAdmin):
    """Read-only: rows are append-only (core.models.AppendOnlyModel)."""

    list_display = ["created_at", "query", "author", "author_user"]
    list_filter = ["author", "created_at"]
    search_fields = ["query__ref", "body"]
    readonly_fields = [f.name for f in QueryMessage._meta.fields]
    inlines = [QueryPhotoInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
