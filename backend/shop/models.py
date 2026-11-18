import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, FileExtensionValidator
from django.utils import timezone

def image_path(instance, filename):
    return "products/"+uuid.uuid4().hex+"."+filename.rsplit(".",1)[-1].lower()
def image_size(value):
    if value.size > 5*1024*1024: raise ValidationError("A imagem deve ter no máximo 5 MB.")
color_validator = RegexValidator(r"^#[0-9a-fA-F]{6}$","Usa uma cor hexadecimal, por exemplo #233e35.")

class Category(models.Model):
    name = models.CharField("Nome",max_length=80,unique=True)
    position = models.PositiveIntegerField("Ordem",default=0)
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["position","name"]
    def __str__(self): return self.name

class Product(models.Model):
    name = models.CharField("Nome",max_length=160)
    slug = models.SlugField("Identificador",max_length=100,unique=True)
    category = models.ForeignKey(Category,on_delete=models.PROTECT,verbose_name="Categoria")
    description = models.TextField("Descrição",blank=True,max_length=2000)
    price = models.DecimalField("Preço (€)",max_digits=9,decimal_places=2,validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField("Stock disponível",default=0,validators=[MaxValueValidator(999999)])
    active = models.BooleanField("Publicado na loja",default=False)
    demo = models.BooleanField("Produto de demonstração",default=False)
    image = models.ImageField("Fotografia",upload_to=image_path,blank=True,
        validators=[image_size,FileExtensionValidator(["jpg","jpeg","png","webp"])],
        help_text="JPG, PNG ou WebP, até 5 MB. Sem imagem, é usada a ilustração escolhida.")
    illustration = models.CharField("Ilustração",max_length=20,default="vase",
        choices=[("vase","Jarra"),("bag","Saco"),("book","Caderno"),("mug","Caneca"),("bottle","Garrafa")])
    color = models.CharField("Cor do objeto",max_length=7,default="#a7b193",validators=[color_validator])
    background = models.CharField("Cor de fundo",max_length=7,default="#e7e8df",validators=[color_validator])
    position = models.PositiveIntegerField("Ordem no catálogo",default=0)
    updated_at = models.DateTimeField("Atualizado em",auto_now=True)
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["position","name"]
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0),name="product_price_positive")]
    def __str__(self): return self.name

class Order(models.Model):
    STATUSES = [("draft","Rascunho"),("confirmed","Confirmada"),("shipped","Enviada"),("completed","Concluída"),("cancelled","Cancelada")]
    customer_name = models.CharField("Nome do cliente",max_length=160)
    email = models.EmailField("Email",blank=True)
    phone = models.CharField("Telefone",max_length=40,blank=True)
    address = models.TextField("Morada de entrega",blank=True,max_length=1500)
    notes = models.TextField("Notas internas",blank=True,max_length=3000)
    status = models.CharField("Estado",max_length=20,choices=STATUSES,default="draft",editable=False)
    payment = models.CharField("Pagamento (registo manual)",max_length=20,default="pending",
        choices=[("pending","Pendente"),("paid","Pago"),("refunded","Reembolsado")],
        help_text="Apenas regista um pagamento externo. Não cobra nem reembolsa dinheiro.")
    shipping = models.DecimalField("Portes (€)",max_digits=9,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    created_at = models.DateTimeField("Criada em",default=timezone.now,editable=False)
    updated_at = models.DateTimeField("Atualizada em",auto_now=True)
    class Meta:
        verbose_name = "Encomenda"
        verbose_name_plural = "Encomendas"
        ordering = ["-created_at"]
    @property
    def reference(self): return f"N{self.pk:06d}" if self.pk else "Nova encomenda"
    @property
    def total(self): return self.shipping+sum((line.quantity*line.unit_price for line in self.lines.all()),Decimal("0"))
    def __str__(self): return self.reference

class OrderLine(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="lines")
    product = models.ForeignKey(Product,on_delete=models.PROTECT,verbose_name="Produto")
    product_name = models.CharField("Nome registado",max_length=160,editable=False)
    quantity = models.PositiveIntegerField("Quantidade",default=1,validators=[MinValueValidator(1),MaxValueValidator(9999)])
    unit_price = models.DecimalField("Preço unitário (€)",max_digits=9,decimal_places=2,editable=False)
    class Meta:
        verbose_name = "Artigo"
        verbose_name_plural = "Artigos"
        constraints = [models.UniqueConstraint(fields=["order","product"],name="order_product_unique"),
                       models.CheckConstraint(condition=models.Q(quantity__gte=1),name="line_quantity_positive")]

class StoreSettings(models.Model):
    name = models.CharField("Nome da loja",max_length=50,default="NOVA")
    tagline = models.CharField("Slogan",max_length=140,default="Um novo olhar sobre o essencial")
    headline = models.CharField("Título principal",max_length=160,default="Pequenas coisas. Novos começos.")
    introduction = models.TextField("Apresentação",max_length=1200,default="Estamos a dar forma a uma nova loja. Um espaço para descobrir objetos que encontram lugar no teu dia a dia.")
    contact_email = models.EmailField("Email de contacto público",blank=True)
    class Meta:
        verbose_name = "Dados da loja"
        verbose_name_plural = "Dados da loja"
    def __str__(self): return self.name

class SetupGrant(models.Model):
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

class LoginAttempt(models.Model):
    key = models.CharField(max_length=64,primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
