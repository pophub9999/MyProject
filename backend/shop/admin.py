import csv
from decimal import Decimal
from django.contrib import admin,messages
from django.contrib.auth.admin import UserAdmin,GroupAdmin
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html
from .models import Category,Product,Order,OrderLine,StoreSettings
from .services import transition

class StoreAdminSite(admin.AdminSite):
    site_header="NOVA · Gestão da loja"
    site_title="Backoffice"
    index_title="Visão geral"
    def index(self,request,extra_context=None):
        extra_context=extra_context or {}
        if request.user.has_perm("shop.view_product") and request.user.has_perm("shop.view_order"):
            extra_context["stats"]={
                "products":Product.objects.filter(active=True).count(),
                "low_stock":Product.objects.filter(active=True,stock__lte=5).count(),
                "orders":Order.objects.filter(status__in=["draft","confirmed"]).count(),
                "paid":sum((o.total for o in Order.objects.filter(payment="paid").exclude(status="cancelled").prefetch_related("lines")),Decimal("0"))}
        return super().index(request,extra_context)
site=StoreAdminSite(name="admin")
site.register(User,UserAdmin)
site.register(Group,GroupAdmin)

@admin.register(Category,site=site)
class CategoryAdmin(admin.ModelAdmin):
    list_display=("name","position")
    search_fields=("name",)

@admin.register(Product,site=site)
class ProductAdmin(admin.ModelAdmin):
    list_display=("thumbnail","name","category","price","stock","active","demo")
    list_filter=("active","demo","category")
    search_fields=("name","slug","description")
    prepopulated_fields={"slug":("name",)}
    readonly_fields=("updated_at",)
    list_per_page=30
    fieldsets=(
        ("Produto",{"fields":("name","slug","category","description")}),
        ("Preço e disponibilidade",{"fields":("price","stock","active","demo","position"),
            "description":"O stock é descontado ao confirmar uma encomenda. O carrinho público continua a ser uma simulação."}),
        ("Imagem",{"fields":("image","illustration","color","background")}),
        ("Histórico",{"fields":("updated_at",)}))
    @admin.display(description="Imagem")
    def thumbnail(self,obj):
        if obj.image: return format_html('<img src="{}" width="40" height="40" style="object-fit:cover;border-radius:6px" alt="">',obj.image.url)
        return "—"
    def has_delete_permission(self,request,obj=None): return False

class LineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors): return
        if not any(f.cleaned_data and not f.cleaned_data.get("DELETE") for f in self.forms):
            raise ValidationError("Adiciona pelo menos um artigo.")
        if self.instance.pk and Order.objects.get(pk=self.instance.pk).status!="draft":
            if any(f.has_changed() for f in self.forms): raise ValidationError("Os artigos de uma encomenda confirmada não podem ser alterados.")

class LineInline(admin.TabularInline):
    model=OrderLine
    formset=LineFormSet
    extra=1
    autocomplete_fields=("product",)
    readonly_fields=("product_name","unit_price")
    fields=("product","quantity","product_name","unit_price")
    def get_readonly_fields(self,request,obj=None): return self.fields if obj and obj.status!="draft" else self.readonly_fields
    def has_add_permission(self,request,obj=None): return (not obj or obj.status=="draft") and super().has_add_permission(request,obj)
    def has_change_permission(self,request,obj=None): return (not obj or obj.status=="draft") and super().has_change_permission(request,obj)
    def has_delete_permission(self,request,obj=None): return (not obj or obj.status=="draft") and super().has_delete_permission(request,obj)

def csv_safe(value):
    value=str(value)
    return "'"+value if value.lstrip().startswith(("=","+","-","@")) else value

@admin.register(Order,site=site)
class OrderAdmin(admin.ModelAdmin):
    list_display=("reference_label","customer_name","status","payment","amount","created_at")
    list_filter=("status","payment","created_at")
    search_fields=("customer_name","email","phone","id")
    date_hierarchy="created_at"
    readonly_fields=("reference_label","status","amount","created_at","updated_at")
    inlines=(LineInline,)
    actions=("confirm_orders","ship_orders","complete_orders","cancel_orders","export_csv")
    fieldsets=(
        ("Encomenda",{"fields":("reference_label","status","amount"),
            "description":"Guarda um rascunho com os artigos. Na lista de encomendas, seleciona-o e usa Confirmar para descontar stock. Não existe checkout ou pagamento online."}),
        ("Cliente",{"fields":("customer_name","email","phone","address")}),
        ("Gestão",{"fields":("shipping","payment","notes")}),
        ("Registo",{"fields":("created_at","updated_at")}))
    def get_readonly_fields(self,request,obj=None): return self.readonly_fields+(("shipping",) if obj and obj.status!="draft" else ())
    def get_queryset(self,request): return super().get_queryset(request).prefetch_related("lines")
    @admin.display(description="Referência")
    def reference_label(self,obj): return obj.reference
    @admin.display(description="Total")
    def amount(self,obj): return f"{obj.total:.2f} €" if obj.pk else "Calculado ao guardar"
    def has_delete_permission(self,request,obj=None): return False
    def save_formset(self,request,form,formset,change):
        instances=formset.save(commit=False)
        for obj in formset.deleted_objects: obj.delete()
        for line in instances:
            if not line.pk or "product" in next((f.changed_data for f in formset.forms if f.instance is line),[]):
                line.product_name=line.product.name
                line.unit_price=line.product.price
            line.save()
        formset.save_m2m()
    def change_states(self,request,queryset,target):
        for order in queryset:
            try:
                updated=transition(order.pk,target)
                self.log_change(request,updated,f"Estado alterado para {updated.get_status_display()}")
                self.message_user(request,f"{order.reference}: {updated.get_status_display()}.",messages.SUCCESS)
            except ValidationError as exc: self.message_user(request,f"{order.reference}: {' '.join(exc.messages)}",messages.ERROR)
    @admin.action(description="Confirmar e descontar stock",permissions=["change"])
    def confirm_orders(self,request,queryset): self.change_states(request,queryset,"confirmed")
    @admin.action(description="Marcar como enviada",permissions=["change"])
    def ship_orders(self,request,queryset): self.change_states(request,queryset,"shipped")
    @admin.action(description="Marcar como concluída",permissions=["change"])
    def complete_orders(self,request,queryset): self.change_states(request,queryset,"completed")
    @admin.action(description="Cancelar e repor stock reservado",permissions=["change"])
    def cancel_orders(self,request,queryset): self.change_states(request,queryset,"cancelled")
    @admin.action(description="Exportar selecionadas em CSV",permissions=["view"])
    def export_csv(self,request,queryset):
        response=HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"]='attachment; filename="encomendas.csv"'
        response.write("\ufeff")
        writer=csv.writer(response,delimiter=";")
        writer.writerow(["Referência","Cliente","Email","Estado","Pagamento","Total EUR","Data"])
        for o in queryset: writer.writerow([csv_safe(x) for x in [o.reference,o.customer_name,o.email,o.get_status_display(),o.get_payment_display(),str(o.total),o.created_at.isoformat()]])
        return response

@admin.register(StoreSettings,site=site)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display=("name","tagline","contact_email")
    def has_add_permission(self,request): return not StoreSettings.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self,request,obj=None): return False
