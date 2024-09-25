from django.conf import settings
from django.contrib import messages


def common(request):
    return {
        "INFO_MESSAGES": messages.get_messages(request),
        "AP_PREDICT_LDAP": settings.AP_PREDICT_LDAP,
    }
