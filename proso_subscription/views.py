from .models import Subscription, SubscriptionPlan, SubscriptionPlanDescription, DiscountCode
from calendar import monthrange
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from gopay.enums import PaymentStatus
from proso.django.request import get_language
from proso.django.response import render_json


def plans(request):
    lang = get_language(request)
    discount_code = get_discount_code(request)
    if discount_code is not None:
        discount_code.is_valid(request.user, throw_exception=True)
    return render_json(
        request,
        [p.to_json(lang=lang, discount_code=discount_code) for p in SubscriptionPlan.objects.prepare_related().filter(active=True)],
        template='subscription_json.html'
    )


@staff_member_required
def revenue_per_month(request, currency):
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        import matplotlib.pyplot as plt
        import pandas
        import seaborn as sns
    except ImportError:
        return HttpResponse('Can not import python packages for analysis.', status=503)
    now = datetime.now()
    ago = int(request.GET.get('ago', 0))
    today = now.replace(hour=0, minute=0, second=0, microsecond=0) - relativedelta(months=ago)
    subscriptions = Subscription.objects.prepare_related().filter(
        payment__state=PaymentStatus.PAID,
        expiration__gte=today
    )
    data = []
    for sub in subscriptions:
        expiration = sub.payment.updated + relativedelta(months=sub.plan_description.plan.months_validity)
        first_month_days = monthrange(sub.payment.updated.year, sub.payment.updated.month)[1]
        last_month_days = monthrange(expiration.year, expiration.month)[1]
        record = {
            'paid': sub.payment.updated,
            'expiration': expiration,
            'revenue': sub.payment.status['amount'] / 100,
            'currency': sub.payment.status['currency'],
            'months': sub.plan_description.plan.months_validity,
            'first_percentage': (first_month_days- sub.payment.updated.day + 1) / first_month_days,
            'last_percentage': expiration.day / last_month_days,
        }
        percentage_total = record['first_percentage'] + record['last_percentage']
        record['first_percentage'] /= percentage_total
        record['last_percentage'] /= percentage_total
        data.append(record)
    data = pandas.DataFrame(data)
    data = data[data['currency'] == currency]
    result = []
    for i in range(12 + ago):
        month = (today.month + i) % 12
        if month == 0:
            month = 12
        year = today.year if month >= today.month else (today.year + 1)
        month_data = data[
            data['paid'].apply(lambda p: p.year < year or (p.month <= month and p.year == year)) &
            data['expiration'].apply(lambda e: e.year > year or (e.month >= month and e.year == year))
        ]
        if len(month_data) == 0:
            result.append({
                'year_month': '{}-{}'.format(year, month if month > 9 else '0{}'.format(month)),
                'revenue': 0,
                'currency': currency,
                'count': 0,
                'percentage': 0,
            })
        for paid, expiration, revenue, currency, months, first_percentage, last_percentage in month_data[['paid', 'expiration', 'revenue', 'currency', 'months', 'first_percentage', 'last_percentage']].values:
            percentage = 1.0
            if expiration.year == year and expiration.month == month:
                percentage = last_percentage
            elif paid.year == year and paid.month == month:
                percentage = first_percentage
            result.append({
                'year_month': '{}-{}'.format(year, month if month > 9 else '0{}'.format(month)),
                'revenue': (revenue / months) * percentage,
                'currency': currency,
                'percentage': percentage,
                'count': 1,
            })
    result = pandas.DataFrame(result)

    def _apply(group):
        return pandas.DataFrame([{
            'revenue': group['revenue'].sum(),
            'count': group['count'].sum(),
            'percentage': group['percentage'].sum(),
        }])
    sns.set(style='white')
    result = result.groupby(['year_month', 'currency']).apply(_apply).reset_index()
    fig = plt.figure()
    sns.barplot(x='year_month', y='revenue', data=result, color=sns.color_palette()[0], label='Average revenue')
    plt.legend()
    plt.xticks(rotation=90)
    plt.xlabel('Year-Month')
    plt.ylabel('Revenue ({})'.format(currency))
    plt.twinx()
    sns.pointplot(result['year_month'], result['count'], linestyles='--', color='black', label='Number of subscriptions')
    plt.ylim(0, 1.2 * result['count'].max())
    plt.ylabel('Number of subscriptions')
    plt.tight_layout()
    plt.title('Total revenue: {}'.format(result['revenue'].sum()))
    response = HttpResponse(content_type='image/png')
    canvas = FigureCanvas(fig)
    canvas.print_png(response)
    return response


def discount_code_view(request, code):
    return render_json(
        request,
        get_object_or_404(DiscountCode, code=DiscountCode.objects.prepare_code(code), active=True).to_json(),
        template='subscription_json.html'
    )


@login_required()
def my_referrals(request):
    return render_json(
        request,
        [s.to_json(confidential=True) for s in request.user.referred_subscriptions.order_by('-created').filter(payment__state=PaymentStatus.PAID)],
        template='subscription_json.html'
    )


@login_required()
@transaction.atomic
def subscribe(request, description_id):
    return_url = request.GET.get('return_url', request.META['HTTP_HOST'])
    description = get_object_or_404(SubscriptionPlanDescription, id=description_id)
    discount_code = get_discount_code(request)
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


def get_discount_code(request):
    return get_object_or_404(DiscountCode, code=DiscountCode.objects.prepare_code(request.GET.get('discount_code')), active=True) if 'discount_code' in request.GET else None
