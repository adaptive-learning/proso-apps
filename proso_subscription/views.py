from .models import Subscription, SubscriptionPlan, SubscriptionPlanDescription, DiscountCode
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, Http404
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
    today_month = now.replace(hour=0, minute=0, second=0, microsecond=0, day=1) - relativedelta(months=ago)
    subscriptions = Subscription.objects.prepare_related().filter(
        payment__state=PaymentStatus.PAID,
        expiration__gte=today_month
    )
    data = []
    for sub in subscriptions:
        expiration = sub.payment.updated + relativedelta(months=sub.plan_description.plan.months_validity)
        record = {
            'paid': sub.payment.updated,
            'expiration': expiration,
            'revenue': sub.payment.status['amount'] / 100,
            'currency': sub.payment.status['currency'],
            'months': sub.plan_description.plan.months_validity,
        }
        data.append(record)
    data = pandas.DataFrame(data)
    if len(data) == 0:
        raise Http404("There are no active subscriptions.")
    print(data)
    data = data[data['currency'] == currency]
    data['year_month'] = data['paid'].apply(lambda x: pandas.to_datetime(str(x)).strftime('%Y-%m'))

    def _apply(group):
        return pandas.DataFrame([{
            'revenue': group['revenue'].sum(),
            'count': len(group),
        }])
    result = data.groupby('year_month').apply(_apply).reset_index()
    counts = []
    for year_month in [today_month + relativedelta(months=i) for i in range(12 + ago)]:
        year = year_month.year
        month = year_month.month
        year_month_data = data[
            data['paid'].apply(lambda p: p.year < year or (p.month <= month and p.year == year)) &
            data['expiration'].apply(lambda e: e.year > year or (e.month >= month and e.year == year))
        ]
        counts.append({
            'year_month': year_month.strftime('%Y-%m'),
            'count_dist': len(year_month_data),
        })
    result = pandas.merge(pandas.DataFrame(counts), result, on='year_month', how='left').fillna(0)

    print(result)
    sns.set(style='white')
    fig = plt.figure()
    sns.barplot(x='year_month', y='revenue', data=result, color=sns.color_palette()[0], label='Revenue')
    plt.legend()
    plt.xticks(rotation=90)
    plt.xlabel('Year-Month')
    plt.ylabel('Revenue ({})'.format(currency))
    plt.twinx()
    sns.pointplot(result['year_month'], result['count'], linestyles='--', color='black', label='Number of subscriptions')
    sns.pointplot(result['year_month'], result['count_dist'], linestyles=':', color='red', label='Number of subscriptions (dist)')
    plt.ylim(0, 1.2 * max(result['count'].max(), result['count_dist'].max()))
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
