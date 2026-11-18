import hashlib,os,secrets
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from shop.models import Category,Product,StoreSettings,SetupGrant

class Command(BaseCommand):
    help="Seed the initial catalogue once and prepare an owner-only setup token."
    def handle(self,*args,**kwargs):
        with transaction.atomic():
            settings,created=StoreSettings.objects.get_or_create(pk=1)
            if created:
                rows=[
                    ("jarra","Jarra Forma","Casa","24.00","#e7e8df","vase","#c9b69b"),
                    ("saco","Saco Essencial","Dia a dia","18.00","#ece5d9","bag","#a7b193"),
                    ("caderno","Caderno Pausa","Papelaria","12.50","#e2e6dc","book","#61785e"),
                    ("caneca","Caneca Calma","Casa","16.00","#eee5dc","mug","#bc8b72"),
                    ("garrafa","Garrafa Ritmo","Dia a dia","22.00","#e0e5e1","bottle","#778f87"),
                    ("bloco","Bloco Ideias","Papelaria","9.50","#ece9d8","book","#c4ab68")]
                for i,(slug,name,cat,price,bg,kind,color) in enumerate(rows):
                    category,_=Category.objects.get_or_create(name=cat)
                    Product.objects.get_or_create(slug=slug,defaults=dict(name=name,category=category,price=Decimal(price),
                        stock=10,active=True,demo=True,position=i,background=bg,illustration=kind,color=color))
            if not get_user_model().objects.filter(is_superuser=True).exists():
                grant=SetupGrant.objects.filter(pk=1).first()
                if not grant or (not grant.used and grant.expires_at<=timezone.now()):
                    token=secrets.token_urlsafe(40)
                    SetupGrant.objects.update_or_create(pk=1,defaults={"token_hash":hashlib.sha256(token.encode()).hexdigest(),
                        "expires_at":timezone.now()+timedelta(hours=48),"used":False})
                    path=Path(os.environ.get("SETUP_TOKEN_FILE","/data/setup-token"))
                    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                    with os.fdopen(fd,"w") as out: out.write(token)
        self.stdout.write("Catalogue initialized. Setup token remains on the server only.")
