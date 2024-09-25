from django.contrib import messages
from django.conf import settings


def common(request):
    return {
        "INFO_MESSAGES": messages.get_messages(request),
        "AP_PREDICT_LDAP": settings.AP_PREDICT_LDAP,
    }
