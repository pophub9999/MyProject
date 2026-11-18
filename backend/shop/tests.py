import hashlib
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase,Client,override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from .models import Category,Product,Order,OrderLine,SetupGrant,StoreSettings
from .services import transition

@override_settings(SECURE_SSL_REDIRECT=False)
class StoreTests(TestCase):
    def setUp(self):
        self.category=Category.objects.create(name="Casa")
        self.product=Product.objects.create(name="Jarra",slug="jarra",category=self.category,price=Decimal("24"),stock=10,active=True)
        self.user=get_user_model().objects.create_superuser("owner","owner@example.com","Strong-Passphrase-2026!")
    def order(self,quantity=2):
        order=Order.objects.create(customer_name="Cliente teste")
        OrderLine.objects.create(order=order,product=self.product,product_name=self.product.name,quantity=quantity,unit_price=self.product.price)
        return order
    def test_private_admin_and_public_catalog(self):
        self.assertEqual(self.client.get("/admin/").status_code,302)
        Product.objects.create(name="Oculto",slug="hidden",category=self.category,price=5,stock=10)
        data=self.client.get("/api/catalog/").json()
        self.assertEqual(len(data["products"]),1)
        self.assertEqual(data["products"][0]["price"],2400)
    def test_product_edit_updates_catalog(self):
        self.client.force_login(self.user)
        response=self.client.post(f"/admin/shop/product/{self.product.pk}/change/",{
            "name":"Nova jarra","slug":"jarra","category":self.category.pk,"description":"Descrição",
            "price":"27.50","stock":"8","active":"on","demo":"on","illustration":"vase",
            "color":"#112233","background":"#eeeeee","position":"0","_save":"Guardar"})
        self.assertEqual(response.status_code,302)
        data=self.client.get("/api/catalog/").json()["products"][0]
        self.assertEqual((data["price"],data["stock"],data["name"]),(2750,8,"Nova jarra"))
    def test_confirm_cancel_once(self):
        order=self.order()
        transition(order.pk,"confirmed")
        self.product.refresh_from_db();self.assertEqual(self.product.stock,8)
        with self.assertRaises(ValidationError): transition(order.pk,"confirmed")
        transition(order.pk,"cancelled")
        self.product.refresh_from_db();self.assertEqual(self.product.stock,10)
        with self.assertRaises(ValidationError): transition(order.pk,"cancelled")
        self.product.refresh_from_db();self.assertEqual(self.product.stock,10)
    def test_insufficient_stock_rolls_back(self):
        order=self.order()
        other=Product.objects.create(name="Outro",slug="other",category=self.category,price=3,stock=0)
        OrderLine.objects.create(order=order,product=other,product_name=other.name,quantity=1,unit_price=3)
        with self.assertRaises(ValidationError): transition(order.pk,"confirmed")
        self.product.refresh_from_db();order.refresh_from_db()
        self.assertEqual(self.product.stock,10);self.assertEqual(order.status,"draft")
    def test_shipped_not_cancelled(self):
        order=self.order();transition(order.pk,"confirmed");transition(order.pk,"shipped")
        with self.assertRaises(ValidationError): transition(order.pk,"cancelled")
        transition(order.pk,"completed")
    def test_price_snapshot(self):
        order=self.order();self.product.price=Decimal("99");self.product.save()
        self.assertEqual(order.total,Decimal("48"))
    def order_payload(self):
        return {"customer_name":"Cliente manual","email":"","phone":"","address":"","notes":"","payment":"pending","shipping":"3.00",
            "lines-TOTAL_FORMS":"1","lines-INITIAL_FORMS":"0","lines-MIN_NUM_FORMS":"0","lines-MAX_NUM_FORMS":"1000",
            "lines-0-product":str(self.product.pk),"lines-0-quantity":"2","_save":"Guardar"}
    def test_admin_creates_and_confirms_order(self):
        self.client.force_login(self.user)
        response=self.client.post("/admin/shop/order/add/",self.order_payload())
        self.assertEqual(response.status_code,302, response.context and str(response.context.get("errors")))
        order=Order.objects.get(customer_name="Cliente manual")
        self.assertEqual(order.total,Decimal("51"))
        self.product.refresh_from_db();self.assertEqual(self.product.stock,10)
        self.client.post("/admin/shop/order/",{"action":"confirm_orders","_selected_action":[order.pk],"index":"0"})
        self.product.refresh_from_db();self.assertEqual(self.product.stock,8)
    def test_forms_render(self):
        self.client.force_login(self.user)
        order=self.order();transition(order.pk,"confirmed")
        for path in ["/admin/","/admin/shop/product/","/admin/shop/product/add/","/admin/shop/order/add/",
                     f"/admin/shop/order/{order.pk}/change/","/admin/shop/category/","/admin/shop/storesettings/","/admin/auth/user/"]:
            self.assertEqual(self.client.get(path).status_code,200,path)
    def test_login_throttle(self):
        for i in range(10): self.assertEqual(self.client.post("/admin/login/",{"username":"wrong","password":"wrong"}).status_code,200)
        self.assertEqual(self.client.post("/admin/login/",{"username":"wrong","password":"wrong"}).status_code,429)
    def test_csrf_required(self):
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/admin/login/",{"username":"owner","password":"Strong-Passphrase-2026!"}).status_code,403)
    def test_svg_rejected(self):
        from django.forms import modelform_factory
        form=modelform_factory(Product,fields=["image"])(files={"image":SimpleUploadedFile("bad.svg",b"<svg><script>alert(1)</script></svg>",content_type="image/svg+xml")})
        self.assertFalse(form.is_valid())
    def test_settings_and_read_only_api(self):
        StoreSettings.objects.create(name="Minha marca",contact_email="loja@example.com")
        self.assertEqual(self.client.get("/api/catalog/").json()["settings"]["name"],"Minha marca")
        self.assertEqual(self.client.post("/api/catalog/",{}).status_code,405)
    def test_csv_escape(self):
        from .admin import csv_safe
        self.assertEqual(csv_safe("=1+1"),"'=1+1")
    def test_bootstrap_not_reset_stock(self):
        StoreSettings.objects.create(pk=1);self.product.stock=7;self.product.save()
        call_command("bootstrap")
        self.product.refresh_from_db();self.assertEqual(self.product.stock,7)

@override_settings(SECURE_SSL_REDIRECT=False)
class SetupTests(TestCase):
    def setUp(self):
        SetupGrant.objects.create(pk=1,token_hash=hashlib.sha256(b"private-test-token").hexdigest(),expires_at=timezone.now()+timedelta(hours=1))
    def payload(self,token="private-test-token"):
        return {"token":token,"username":"manager","email":"manager@example.com","password1":"Unique-long-Passphrase-2037!","password2":"Unique-long-Passphrase-2037!"}
    def test_invalid_token(self):
        self.assertEqual(self.client.post("/setup/",self.payload("wrong")).status_code,200)
        self.assertEqual(get_user_model().objects.count(),0)
    def test_setup_once_hashed_password(self):
        self.assertEqual(self.client.post("/setup/",self.payload()).status_code,302)
        user=get_user_model().objects.get();self.assertTrue(user.is_superuser)
        self.assertNotEqual(user.password,self.payload()["password1"])
        self.client.logout();self.client.post("/setup/",self.payload())
        self.assertEqual(get_user_model().objects.count(),1)
        self.assertTrue(SetupGrant.objects.get(pk=1).used)
    def test_expired_token(self):
        SetupGrant.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.client.post("/setup/",self.payload());self.assertEqual(get_user_model().objects.count(),0)
    def test_csrf(self):
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/setup/",self.payload()).status_code,403)
    def test_weak_password(self):
        d=self.payload();d.update(password1="123",password2="123")
        self.client.post("/setup/",d);self.assertEqual(get_user_model().objects.count(),0)
