from django import template
from django.conf import settings


register = template.Library()


@register.simple_tag(takes_context=True)
def can_edit(context, file):
    user = context['user']
    return (file.author == user or (getattr(file, 'predefined', None) and user.is_superuser))


@register.simple_tag(takes_context=False)
def hosting_info():
    return settings.HOSTING_INFO


@register.simple_tag(takes_context=False)
def contact_mailto():
    return settings.CONTACT_MAILTO


@register.simple_tag(takes_context=False)
def contact_text():
    return settings.CONTACT_TEXT


@register.simple_tag(takes_context=False)
def privacy_notice():
    return settings.PIVACY_NOTICE
