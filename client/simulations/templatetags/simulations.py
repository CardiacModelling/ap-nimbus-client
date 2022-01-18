from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def can_edit(context, file):
    user = context['user']
    return file.is_editable_by(user)
