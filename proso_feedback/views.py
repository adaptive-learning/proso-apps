# -*- coding: utf-8 -*-
from proso.django.request import json_body
from proso.django.response import render, render_json
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.mail import EmailMultiAlternatives
from logging import getLogger
from models import Rating, Comment
from proso_user.models import Session
from lazysignup.decorators import allow_lazy_user
from proso.django.config import get_config
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import ugettext as _


LOGGER = getLogger(__name__)


def is_likely_worthless(feedback):
    return len(feedback['text']) <= 50


@allow_lazy_user
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
        feedback_data['user_agent'] = Session.objects.get_current_session().http_user_agent.content
        if not feedback_data.get('username'):
            feedback_data['username'] = request.user.username
        if not feedback_data.get('email'):
            feedback_data['email'] = request.user.email
        else:
            try:
                validate_email(feedback_data['email'])
            except ValidationError:
                return render_json(
                    request,
                    {'error': _('The given e-mail address is not valid.'), 'error_type': 'invalid_email'},
                    template='feedback_json.html', status=400
                )
        Comment.objects.create(
            username=feedback_data['username'],
            email=feedback_data['email'],
            text=feedback_data['text'])
        if get_config('proso_feedback', 'send_emails', default=True):
            feedback_domain = get_config('proso_feedback', 'domain', required=True)
            feedback_to = get_config('proso_feedback', 'to', required=True)
            if is_likely_worthless(feedback_data):
                mail_from = 'spam@' + feedback_domain
            else:
                mail_from = 'feedback@' + feedback_domain
            text_content = render_to_string("emails/feedback.plain.txt", {
                "feedback": feedback_data,
                "user": request.user,
            })
            html_content = render_to_string("emails/feedback.html", {
                "feedback": feedback_data,
                "user": request.user,
            })
            mail = EmailMultiAlternatives(
                feedback_domain + ' feedback',
                text_content,
                mail_from,
                feedback_to,
            )
            mail.attach_alternative(html_content, "text/html")
            mail.send()
            LOGGER.debug("email sent %s\n", text_content)
        return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


@allow_lazy_user
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
        if data['value'] not in range(1, 4):
            return render_json(
                request,
                {'error': _('The given value is not valid.'), 'error_type': 'invalid_value'},
                template='feedback_json.html', status=400
            )
        rating_object = Rating(
            user=request.user,
            value=data['value'],
        )
        rating_object.save()
        return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))
