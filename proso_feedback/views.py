# -*- coding: utf-8 -*-
from proso.django.request import json_body
from proso.django.response import render, render_json
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.mail import EmailMultiAlternatives
from logging import getLogger
from .models import Rating, Comment
from proso_user.models import Session
from lazysignup.decorators import allow_lazy_user
from proso_common.models import get_config
from django.utils.translation import ugettext as _


LOGGER = getLogger(__name__)


def is_likely_worthless(feedback):
    return len(feedback['text'].split()) <= 5


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
        feedback_data = json_body(request.body.decode("utf-8"))
        feedback_data['user_agent'] = Session.objects.get_current_session().http_user_agent.content
        if not feedback_data.get('username'):
            feedback_data['username'] = request.user.username
        if not feedback_data.get('email'):
            feedback_data['email'] = request.user.email
        comment = Comment.objects.create(
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
            subject = feedback_domain + ' feedback ' + str(comment.id)
            mail = EmailMultiAlternatives(
                subject,
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
            one of the following numbers (how difficult questions are?):
                (1) too easy,
                (2) appropriate,
                (3) too difficult
            or one of the following numbers (how difficult questions should be?):
                (4) much easier
                (5) bit easier
                (6) the same
                (7) bit harder
                (8) much harder
    """
    if request.method == 'GET':
        return render(request, 'feedback_rating.html', {}, help_text=rating.__doc__)
    if request.method == 'POST':
        data = json_body(request.body.decode("utf-8"))
        if data['value'] not in list(range(1, 9)):
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
