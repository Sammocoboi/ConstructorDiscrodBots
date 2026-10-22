from django.contrib import admin

from .models import Invoice, Payment, Plan, Subscription, UsageCounter


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_monthly", "currency", "is_active", "sort_order")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "code")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_end", "cancel_at_period_end")
    list_filter = ("status", "plan")
    search_fields = ("user__email", "external_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "status", "external_id", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("user__email", "external_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "amount", "currency", "status", "issued_at", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("number", "user__email", "external_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(UsageCounter)
class UsageCounterAdmin(admin.ModelAdmin):
    list_display = ("user", "bot", "period_start", "executions", "api_calls")
    list_filter = ("period_start",)
    search_fields = ("user__email", "bot__name")
    readonly_fields = ("id", "created_at", "updated_at")
