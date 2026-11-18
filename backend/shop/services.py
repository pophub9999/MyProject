from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from .models import Order, Product

@transaction.atomic
def transition(order_id, target):
    # IMMEDIATE SQLite transactions acquire the write lock before reading stock.
    order = Order.objects.select_for_update().get(pk=order_id)
    allowed = {"draft":{"confirmed","cancelled"},"confirmed":{"shipped","cancelled"},"shipped":{"completed"},"completed":set(),"cancelled":set()}
    if target not in allowed[order.status]:
        raise ValidationError("Esta mudança de estado não é permitida.")
    lines = list(order.lines.select_related("product"))
    if target == "confirmed":
        if not lines: raise ValidationError("Adiciona pelo menos um artigo antes de confirmar.")
        for line in lines:
            if not Product.objects.filter(pk=line.product_id,stock__gte=line.quantity).update(stock=F("stock")-line.quantity):
                raise ValidationError(f"Stock insuficiente: {line.product_name}.")
    elif target == "cancelled" and order.status == "confirmed":
        for line in lines: Product.objects.filter(pk=line.product_id).update(stock=F("stock")+line.quantity)
    order.status = target
    order.save(update_fields=["status","updated_at"])
    return order
