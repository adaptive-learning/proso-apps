# -*- coding: utf-8 -*-
from django.utils import simplejson
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from logging import getLogger
from django.conf import settings
from models import Rating
from django.views.decorators.http import require_POST


LOGGER = getLogger(__name__)


def is_likely_worthless(feedback):
    return len(feedback['text']) <= 50


@require_POST
def feedback(request):
    feedback = simplejson.loads(request.body)
    if is_likely_worthless(feedback):
        mail_from = 'spam@' + settings.FEEDBACK_DOMAIN
    else:
        mail_from = 'feedback@' + settings.FEEDBACK_DOMAIN

    text_content = render_to_string("emails/feedback.plain.txt", {
        "feedback": feedback,
        "user": request.user,
    })
    html_content = render_to_string("emails/feedback.html", {
        "feedback": feedback,
        "user": request.user,
    })
    mail = EmailMultiAlternatives(
        settings.FEEDBACK_DOMAIN + ' feedback',
        text_content,
        mail_from,
        [settings.FEEDBACK_TO],
    )
    mail.attach_alternative(html_content, "text/html")
    mail.send()
    LOGGER.debug("email sent %s\n", text_content)
    return HttpResponse('ok', status=201)


@require_POST
def rating(request):
    data = simplejson.loads(request.body)
    rating = Rating(
        user=request.user,
        value=data['value'],
    )
    rating.save()
    return HttpResponse('ok', status=201)
