import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Définir le chemin de base du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Clé secrète Django
SECRET_KEY = os.getenv('SECRET_KEY', 'clé_par_défaut_pour_dev')

# Mode de débogage
DEBUG = True

# Hôtes autorisés
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'www.applestore.com']

# Applications installées
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'products.apps.ProductsConfig',  # Votre application personnalisée
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Configuration des URLs
ROOT_URLCONF = 'store.urls'

# Configuration des templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'Templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Configuration WSGI
WSGI_APPLICATION = 'store.wsgi.application'

# Configuration de la base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'apple_store_db',
        'USER': 'postgres',
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

AUTH_PROFILE_MODULE = 'products.UserProfile'

# Validation des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Paramètres de localisation
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'America/Montreal'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOGIN_URL = '/login/'


# Fichiers statiques (CSS, JavaScript, Images)
STATIC_URL = 'store/static/'
STATICFILES_DIRS = [BASE_DIR / 'static/']

# Fichiers média (pour le contenu téléchargé)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Type de clé primaire par défaut
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# Configuration Stripe
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
PAYPAL_PUBLIC_KEY = os.getenv('PAYPAL_PUBLIC_KEY', '')
PAYPAL_SECRET_KEY = os.getenv('PAYPAL_SECRET_KEY', '')


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = os.getenv('SENDGRID_API_KEY')  
DEFAULT_FROM_EMAIL = 'pharellkamgue@gmail.com'

