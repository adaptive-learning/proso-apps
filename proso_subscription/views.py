from .models import Subscription, SubscriptionPlan, SubscriptionPlanDescription
from django.contrib.auth.decorators import login_required
from proso.django.request import get_language
from proso.django.response import render_json
from django.shortcuts import get_object_or_404


def plans(request):
    lang = get_language(request)
    return render_json(
        request,
        [p.to_json(lang=lang) for p in SubscriptionPlan.objects.prepare_related().filter(active=True)],
        template='subscription_json.html'
    )


@login_required()
def subscribe(request, description_id):
    return_url = request.GET.get('return_url', request.META['HTTP_HOST'])
    description = get_object_or_404(SubscriptionPlanDescription, id=description_id)
    subscription = Subscription.objects.subscribe(request.user, description, return_url)
    return render_json(request, subscription.to_json(), template='subscription_json.html', status=202)


@login_required()
def my_subscriptions(request):
    return render_json(
        request,
        [s.to_json() for s in Subscription.objects.prepare_related().filter(user_id=request.user.id)],
        template='subscription_json.html'
    )
