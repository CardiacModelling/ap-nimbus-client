from django.contrib import messages


def common(request):
    return {'INFO_MESSAGES': messages.get_messages(request)}
