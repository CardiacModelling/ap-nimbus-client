from .base_settings import *


DEBUG = False

# Cache templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.common',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader',[
                    'django.template.loaders.filesystem.Loader',
                ]),
            ],
        },
    },
]
