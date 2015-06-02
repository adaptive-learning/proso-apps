from __future__ import absolute_import, unicode_literals
from django.template.loader import render_to_string
import re
from django.conf import settings
from django.utils.encoding import force_text

_HTML_TYPES = ('text/html', 'application/xhtml+xml')


class ToolbarMiddleware(object):

    def process_response(self, request, response):

        if not hasattr(request, "user") or not request.user.is_staff:
            return response

        # Check for responses where the config_bar can't be inserted.
        content_encoding = response.get('Content-Encoding', '')
        content_type = response.get('Content-Type', '').split(';')[0]
        if any((getattr(response, 'streaming', False), 'gzip' in content_encoding, content_type not in _HTML_TYPES)):
            return response

        # Insert the toolbar in the response.
        content = force_text(response.content, encoding=settings.DEFAULT_CHARSET)
        insert_before = '</html>'
        pattern = re.escape(insert_before)
        response.content = re.sub(
            pattern,
            render_to_string('common_toolbar.html') + insert_before,
            content,
            flags=re.IGNORECASE)
        if response.get('Content-Length', None):
            response['Content-Length'] = len(response.content)
        return response
