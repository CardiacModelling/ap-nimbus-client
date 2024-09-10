from django.contrib import messages
from django.conf import settings

def common(request):
    return {
        'INFO_MESSAGES': messages.get_messages(request), 
        'AUTH_USE_LDAP': settings.AUTH_USE_LDAP
    }
