from django import template
from django.templatetags.static import static
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def js_files():

    js_files = []
    if hasattr(settings, 'PROSO_JS_FILES'):
        for f in settings.PROSO_JS_FILES:
            js_files.append('<script src="{}"></script>'.format(static(f)))
    return mark_safe("\n".join(js_files))
