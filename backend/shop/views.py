import hashlib,secrets
from django import forms
from django.contrib.auth import get_user_model,login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.utils import timezone
from django.views.decorators.http import require_GET,require_http_methods
from django.views.decorators.cache import never_cache
from .models import Product,StoreSettings,SetupGrant

@require_GET
def health(request): return JsonResponse({"status":"ok"})

@require_GET
@never_cache
def catalog(request):
    s=StoreSettings.objects.first()
    products=[{"id":p.slug,"name":p.name,"category":p.category.name,"description":p.description,
               "price":int(p.price*100),"stock":p.stock,"demo":p.demo,"image":p.image.url if p.image else "",
               "bg":p.background,"color":p.color,"type":p.illustration}
              for p in Product.objects.filter(active=True).select_related("category")]
    return JsonResponse({"products":products,"settings":{"name":s.name,"tagline":s.tagline,"headline":s.headline,
                         "introduction":s.introduction,"contact_email":s.contact_email} if s else {}})

class SetupForm(UserCreationForm):
    token=forms.CharField(widget=forms.HiddenInput,max_length=200)
    email=forms.EmailField(label="Email")
    class Meta(UserCreationForm.Meta):
        fields=("username","email","password1","password2")

@never_cache
@require_http_methods(["GET","POST"])
def setup(request):
    if get_user_model().objects.filter(is_superuser=True).exists(): return redirect("/admin/")
    form=SetupForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            grant=SetupGrant.objects.select_for_update().filter(pk=1,used=False,expires_at__gt=timezone.now()).first()
            digest=hashlib.sha256(form.cleaned_data["token"].encode()).hexdigest()
            if not grant or not secrets.compare_digest(grant.token_hash,digest):
                form.add_error(None,"A ligação de ativação é inválida ou expirou.")
            elif get_user_model().objects.filter(is_superuser=True).exists(): return redirect("/admin/")
            else:
                user=form.save(commit=False)
                user.is_staff=user.is_superuser=True
                user.save()
                grant.used=True
                grant.save(update_fields=["used"])
                login(request,user)
                return redirect("/admin/")
    return render(request,"setup.html",{"form":form})
