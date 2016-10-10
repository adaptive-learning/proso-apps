from .models import Subscription, SubscriptionPlan, SubscriptionPlanDescription, DiscountCode
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from proso.django.request import get_language
from proso.django.response import render_json


def plans(request):
    lang = get_language(request)
    return render_json(
        request,
        [p.to_json(lang=lang) for p in SubscriptionPlan.objects.prepare_related().filter(active=True)],
        template='subscription_json.html'
    )


@login_required()
@transaction.atomic
def subscribe(request, description_id):
    return_url = request.GET.get('return_url', request.META['HTTP_HOST'])
    description = get_object_or_404(SubscriptionPlanDescription, id=description_id)
    discount_code = get_object_or_404(DiscountCode, code=DiscountCode.objects.prepare_code(request.GET.get('discount_code')), active=True) if 'discount_code' in request.GET else None
    subscription = Subscription.objects.subscribe(
        request.user, description, discount_code,
        get_referral_user(request), return_url
    )
    return render_json(request, subscription.to_json(), template='subscription_json.html', status=202)


@login_required()
def my_subscriptions(request):
    return render_json(
        request,
        [s.to_json() for s in Subscription.objects.prepare_related().filter(user_id=request.user.id).order_by('-created')],
        template='subscription_json.html'
    )


def get_referral_user(request):
    if 'referral_user' in request.GET:
        return get_object_or_404(User, pk=int(request.GET['referral_user']))
    if 'referral_username' in request.GET:
        return get_object_or_404(User, username=request.GET['referral_username'])
    if 'referral_email' in request.GET:
        return get_object_or_404(User, email=request.GET['referral_email'])
    return None
