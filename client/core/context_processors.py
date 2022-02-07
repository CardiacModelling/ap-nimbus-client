from django.contrib import messages


def common(request):
    info_messages = []
    error_messages = []
    for message in messages.get_messages(request):
        if message.level == messages.ERROR:
            error_messages.append(message)
        elif message.level == messages.INFO:
            info_messages.append(message)

    return {
        'ERROR_MESSAGES': error_messages,
        'INFO_MESSAGES': info_messages,
    }
