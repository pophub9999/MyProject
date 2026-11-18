from django.urls import path
from shop.admin import site
from shop import views
urlpatterns = [path("admin/",site.urls),path("api/catalog/",views.catalog),path("setup/",views.setup),path("health/",views.health)]
