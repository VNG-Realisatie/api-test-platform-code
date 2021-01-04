import os

# Django-hijack (and Django-hijack-admin)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from celery.schedules import crontab

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DJANGO_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
BASE_DIR = os.path.abspath(os.path.join(DJANGO_PROJECT_DIR, os.path.pardir, os.path.pardir))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '-tu6q!6cvp@pe5!97e1i##lmp_%yxjj$k20*ul+ac^u(p2)clj'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = "/accounts/login/"


# Application definition

INSTALLED_APPS = [

    # Note: contenttypes should be first, see Django ticket #10827
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',

    # Note: If enabled, at least one Site object is required
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Optional applications.
    'django.contrib.flatpages',
    'ckeditor',
    'ordered_model',
    'guardian',
    'django_admin_index',
    'django.contrib.admin',
    'registration',
    'subdomains',
    'mathfilters',
    # 'django.contrib.admindocs',
    # 'django.contrib.humanize',
    # 'django.contrib.sitemaps',

    # External applications.
    # 'axes',
    'sniplates',
    'captcha',
    'filer',
    'mptt',
    'hijack',
    'tinymce',
    'compat',  # Part of hijack
    'hijack_admin',
    'elasticapm.contrib.django',
    'easy_thumbnails',
    'django_bootstrap_breadcrumbs',
    'mobetta',
    'crispy_forms',

    # Rest Framework
    'drf_spectacular',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'corsheaders',

    # Project applications.
    'vng.accounts',
    'vng.utils',
    'vng.testsession',
    'vng.api_authentication',
    'vng.servervalidation',
    'vng.postman',
    'vng.design_rules',
    # Disabled for the moment, enable if want to use its functionalities
    # 'vng.openApiInspector',
    'vng.celery',
    'vng.k8s_manager',
    'vng.api',
    'vng',
]

TINYMCE_DEFAULT_CONFIG = {
    'plugins': "table,spellchecker,paste,searchreplace",
    'theme': "advanced",
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 10,
    'width': '100%',
    'height': 500,
    'theme_advanced_resizing': True
}

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'vng.api_authentication.authentication.CustomTokenAuthentication',
    ],
}

SITE_ID = 1

APPEND_SLASH = True

MIDDLEWARE = [
    'elasticapm.contrib.django.middleware.TracingMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',
    'subdomains.middleware.SubdomainURLRoutingMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'vng.utils.middleware.APIVersionHeaderMiddleware',
]

ROOT_URLCONF = 'vng.urls'

SUBDOMAIN_URLCONFS = {
    '*': 'vng.testsession.urls_api_sub',
}

SUBDOMAIN_SEPARATOR = '-'

DEFAULT_URL_SCHEME = 'https'

# List of callables that know how to import templates from various sources.
RAW_TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'admin_tools.template_loaders.Loader',
)


DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(DJANGO_PROJECT_DIR, 'templates'),
        ],
        'APP_DIRS': False,  # conflicts with explicity specifying the loaders
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'vng.utils.context_processors.settings',
                'vng.utils.context_processors.api_list',
                'vng.utils.context_processors.shields_url',
                # REQUIRED FOR ADMIN INDEX
                'django_admin_index.context_processors.dashboard',
            ],
            'loaders': RAW_TEMPLATE_LOADERS
        },
    },
]

WSGI_APPLICATION = 'vng.wsgi.application'

# Database: Defined in target specific settings files.
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGES = (
    ('en', _('English')),
    ('nl', _('Nederlands')),
)


LANGUAGE_CODE = 'en'

TIME_ZONE = 'Europe/Amsterdam'

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = True

# Translations
LOCALE_PATHS = (
    os.path.join(DJANGO_PROJECT_DIR, 'conf', 'locale'),
    os.path.join(BASE_DIR, 'src', 'locale')
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/atvstatic/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(DJANGO_PROJECT_DIR, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

POSTMAN_ROOT = os.path.join(BASE_DIR, 'postman_collection')

MEDIA_URL = '/atvmedia/'

FIXTURE_DIRS = (
    os.path.join(DJANGO_PROJECT_DIR, 'fixtures'),
)

DEFAULT_FROM_EMAIL = 'test@maykinmedia.nl'
EMAIL_TIMEOUT = 10

LOGGING_DIR = os.path.join(BASE_DIR, 'log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s'
        },
        'timestamped': {
            'format': '%(asctime)s %(levelname)s %(name)s  %(message)s'
        },
        'simple': {
            'format': '%(levelname)s  %(message)s'
        },
        'performance': {
            'format': '%(asctime)s %(process)d | %(thread)d | %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'timestamped'
        },
        'django': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGGING_DIR, 'django.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10
        },
        'project': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGGING_DIR, 'vng.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10
        },
        'performance': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGGING_DIR, 'performance.log'),
            'formatter': 'performance',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10
        },
    },
    'loggers': {
        'vng': {
            'handlers': ['project'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['django'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

MEDIA_FOLDER_FILES = {
    'test_scenario': '/files/uploaded_files',
    'test_session': '/files/uploaded_files',
    'servervalidation_log': '/files/log',
    'testsession_log': '/files/log',
}

#
# Additional Django settings
#

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Allow logging in with both username+password and email+password
AUTHENTICATION_BACKENDS = [
    'vng.accounts.backends.UserModelEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]

#
# Custom settings
#
PROJECT_NAME = 'vng'
ENVIRONMENT = None
SHOW_ALERT = True

RUN_KUBERNETES_CMD = False

#
# Library settings
#

ADMIN_INDEX_SHOW_REMAINING_APPS = True

# Django-axes
AXES_LOGIN_FAILURE_LIMIT = 30  # Default: 3
AXES_LOCK_OUT_AT_FAILURE = True  # Default: True
AXES_USE_USER_AGENT = False  # Default: False
AXES_COOLOFF_TIME = 1  # One hour
AXES_BEHIND_REVERSE_PROXY = True  # Default: False (we are typically using Nginx as reverse proxy)
AXES_ONLY_USER_FAILURES = False  # Default: False (you might want to block on username rather than IP)
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = False  # Default: False (you might want to block on username and IP)


HIJACK_LOGIN_REDIRECT_URL = '/'
HIJACK_LOGOUT_REDIRECT_URL = reverse_lazy('admin:accounts_user_changelist')
HIJACK_REGISTER_ADMIN = False
# This is a CSRF-security risk.
# See: http://django-hijack.readthedocs.io/en/latest/configuration/#allowing-get-method-for-hijack-views
HIJACK_ALLOW_GET_REQUESTS = True

# User registration settings
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_FORM = 'vng.utils.forms.RegistrationCaptcha'
SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']

RECAPTCHA_PUBLIC_KEY = '6LfwbaoUAAAAAJ7Bl5o-7pe9DKluPOLX-URNB821'
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY', 'default')

CELERY_TIMEZONE = 'Europe/Amsterdam'

CELERY_BEAT_SCHEDULE = {
    'task-number-one': {
        'task': 'vng.testsession.task.purge_sessions',
        'schedule': crontab(hour=0, minute=0),
    },
    'scheduled-test-provider': {
        'task': 'vng.servervalidation.task.execute_test_scheduled',
        'schedule': crontab(hour=0, minute=0),
    },
}

# Elastic APM
ELASTIC_APM = {
    'SERVICE_NAME': 'VNG API-Testplatform',
    'SECRET_TOKEN': os.getenv('ELASTIC_APM_SECRET_TOKEN', 'default'),
    'SERVER_URL': os.getenv('ELASTIC_APM_SERVER_URL', 'http://example.com'),
}

CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Custom token creation to support multiple API tokens
REST_AUTH_TOKEN_CREATOR = 'vng.api_authentication.utils.create_token'

SHIELDS_URL = 'https://shields.api-test.nl'

SPECTACULAR_SETTINGS = {
    'TITLE': 'API test platform',
    'DESCRIPTION': """This API can be used to automate provider tests and consumer sessions.

The tutorial for this API can be found [here](https://github.com/VNG-Realisatie/api-test-platform/blob/master/tutorials/API.md)""",
    'VERSION': '1.0.1',
    # 'SERVERS': [
    #     "https://api-test.nl/api/v1",
    # ],
    'PREPROCESSING_HOOKS': [
        "vng.utils.preprocess_exclude_paths.preprocess_exclude_admin_path",
    ],
}

CORS_ALLOW_ALL_ORIGINS = True
