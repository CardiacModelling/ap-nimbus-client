from django.contrib import messages


def common(request):
    info_messages = []
    error_messages = []
    for message in messages.get_messages(request):
        info_messages.append(message)

    return {'INFO_MESSAGES': info_messages}
