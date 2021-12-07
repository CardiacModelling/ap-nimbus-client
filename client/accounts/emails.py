from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send_user_creation_email(user, request):
    """
    Email all admin users when a new user is created
    """


    # Don't email the created user about it
    admins = get_user_model().objects.admins().exclude(pk=user.pk)
    admin_emails = list(admins.values_list('email', flat=True))
    admin_names = list(admins.values_list('full_name', flat=True))
    body = render_to_string(
        'emails/user_created.txt',
        {
            'user': user,
            'protocol': request.scheme,
            'domain': get_current_site(request).domain,
            'admin_names': (', '.join(admin_names))
        }
    )

    email = EmailMessage( subject='[AP Portal] Welcome',
                          body=body,
                          from_email=settings.SERVER_EMAIL,
                          to=[user.email],
                          cc=admin_emails,
    )
    email.send(fail_silently=True)
