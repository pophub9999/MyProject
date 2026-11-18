import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
STORE_HOST = os.environ.get("STORE_HOST", "localhost")
ALLOWED_HOSTS = [STORE_HOST, "localhost", "127.0.0.1", "testserver"]
CSRF_TRUSTED_ORIGINS = ["https://" + STORE_HOST]
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
                  "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","shop"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware",
              "django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware",
              "django.contrib.auth.middleware.AuthenticationMiddleware","shop.middleware.LoginThrottleMiddleware",
              "django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR / "templates"],
    "APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":os.environ.get("DB_PATH","/data/store.sqlite3"),
                       "OPTIONS":{"timeout":30,"transaction_mode":"IMMEDIATE"}}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator","OPTIONS":{"min_length":12}},
    {"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "pt-pt"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = "/static"
STATICFILES_DIRS = [BASE_DIR / "assets"]
MEDIA_URL = "/media/"
MEDIA_ROOT = "/media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO","https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
DATA_UPLOAD_MAX_MEMORY_SIZE = 6*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6*1024*1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
