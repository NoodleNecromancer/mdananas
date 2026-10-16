from .settings import *  # noqa: F403,F401


INSTALLED_APPS = [*INSTALLED_APPS, "export_service"]  # noqa: F405
ROOT_URLCONF = "tests.by_urls"
STATIC_URL = "/static/"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # noqa: F405
        "APP_DIRS": True,
    }
]
