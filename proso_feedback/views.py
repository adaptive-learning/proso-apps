# -*- coding: utf-8 -*-
from proso.django.request import json_body
from proso.django.response import render
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.mail import EmailMultiAlternatives
from logging import getLogger
from django.conf import settings
from models import Rating
from proso_user.models import Session


LOGGER = getLogger(__name__)


def is_likely_worthless(feedback):
    return len(feedback['text']) <= 50


def home(request):
    return render(request, 'feedback_home.html', {})


def feedback(request):
    """
    Send feedback to the authors of the system.

    GET parameters:
        html
            turn on the HTML version of the API

    POST parameters (JSON):
        text:
            the main feedback content
        email (optional):
            user's e-mail
        username (optional):
            user's name
    """
    if request.method == 'GET':
        return render(request, 'feedback_feedback.html', {}, help_text=feedback.__doc__)
    if request.method == 'POST':
        feedback_data = json_body(request.body)
        feedback_data['user_agent'] = Session.objects.get_current_session()['http_user_agent']
        if not feedback_data.get('username'):
            feedback_data['username'] = request.user.username
        if not feedback_data.get('email'):
            feedback_data['email'] = request.user.email
        if is_likely_worthless(feedback_data):
            mail_from = 'spam@' + settings.FEEDBACK_DOMAIN
        else:
            mail_from = 'feedback@' + settings.FEEDBACK_DOMAIN

        text_content = render_to_string("emails/feedback.plain.txt", {
            "feedback": feedback_data,
            "user": request.user,
        })
        html_content = render_to_string("emails/feedback.html", {
            "feedback": feedback_data,
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
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def rating(request):
    """
    Rate the current practice.

    GET parameters:
        html
            turn on the HTML version of the API

    POST parameters (JSON):
        value:
            one of the following numbers:
                (1) too easy,
                (2) appropriate,
                (3) too difficult
    """
    if request.method == 'GET':
        return render(request, 'feedback_rating.html', {}, help_text=rating.__doc__)
    if request.method == 'POST':
        data = json_body(request.body)
        rating_object = Rating(
            user=request.user,
            value=data['value'],
        )
        rating_object.save()
        return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))
