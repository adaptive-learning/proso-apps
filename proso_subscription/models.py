from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import now
from gopay.enums import PaymentStatus
from gopay_django_api.models import Payment
from gopay_django_api.signals import payment_changed
from proso.django.models import disable_for_loaddata
from proso.django.request import get_current_request
from proso.django.response import BadRequestException
from proso_user.models import Session
from django.db.models import Q
import uuid
import string
import random


class SubscriptionPlanManager(models.Manager):

    def prepare_related(self):
        return self.prefetch_related('descriptions')


class SubscriptionPlan(models.Model):

    identifier = models.SlugField()
    months_validity = models.IntegerField()
    months_referral = models.IntegerField(default=0)
    type = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)

    objects = SubscriptionPlanManager()

    def to_json(self, nested=False, lang=None, discount_code=None):
        result = {
            'identifier': self.identifier,
            'id': self.id,
            'object_type': 'subscription_plan',
            'type': self.type,
            'featured': self.featured,
            'active': self.active,
            'months-validity': self.months_validity,
            'months-referral': self.months_referral,
        }
        if not nested:
            if lang is None:
                result['descriptions'] = [d.to_json(nested=True, discount_code=discount_code) for d in self.descriptions.all()]
            else:
                result['description'] = [d.to_json(nested=True, discount_code=discount_code) for d in self.descriptions.all() if d.lang == lang][0]
        return result

    def __str__(self):
        return "{0.identifier}".format(self)


class SubscriptionPlanDescriptionManager(models.Manager):

    def prefetch_related(self):
        return self.select_related('plan')


class SubscriptionPlanDescription(models.Model):

    plan = models.ForeignKey(SubscriptionPlan, related_name='descriptions')
    lang = models.CharField(max_length=2)
    name = models.TextField()
    description = models.TextField()
    price = models.IntegerField()
    currency = models.CharField(max_length=10)

    objects = SubscriptionPlanDescriptionManager()

    def to_json(self, nested=False, discount_code=None):
        result = {
            'id': self.id,
            'object_type': 'subscription_plan_description',
            'lang': self.lang,
            'price': self.price,
            'currency': self.currency,
            'description': self.description,
            'name': self.name,
        }
        if nested:
            result['plan_id'] = self.plan_id
        else:
            result['plan'] = self.plan.to_json(nested=True)
        if discount_code is not None and (discount_code.plan_id is None or discount_code.plan_id == self.plan_id):
            result['price_after_discount'] = discount_code.get_updated_price(self.price)
        return result

    def __str__(self):
        return "{0.name}".format(self)


class DiscountCodeManager(models.Manager):

    def prepare_related(self):
        return self.select_related('plan')

    def prepare_code(self, code):
        return code.upper()

    def generate_code(self, length=20):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


class DiscountCode(models.Model):

    plan = models.ForeignKey(SubscriptionPlan, null=True, blank=True, default=None)
    usage_limit = models.IntegerField(null=True, blank=True, default=None)
    discount_percentage = models.IntegerField()
    code = models.CharField(max_length=100)
    identifier = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    objects = DiscountCodeManager()

    def is_valid(self, user, plan_description=None, throw_exception=False):
        if self.usage_limit is not None and self.subscriptions.all().count() >= self.usage_limit:
            if throw_exception:
                raise BadRequestException('The given discount code has been already used by a maximum number of subscribers.', 'discount_code_limit_exceeded')
            return False
        if user.is_authenticated() and user.subscriptions.filter(Q(discount=self) & (Q(payment__isnull=True) | Q(payment__state__in=[PaymentStatus.PAID, PaymentStatus.CREATED]))).count() > 0:
            if throw_exception:
                raise BadRequestException('The given discount code has been already used by the given user.', 'discount_code_already_used')
            return False
        if self.plan_id is not None and plan_description.plan_id != self.plan_id:
            if throw_exception:
                raise BadRequestException('The given discount code does not match with the given subscription plan.', 'discount_code_does_not_match')
            return False
        return True

    def get_updated_price(self, price):
        return int(round(price * (1 - self.discount_percentage / 100.0)))

    def to_json(self, nested=False):
        result = {
            'object_type': 'subscription_discount_code',
            'id': self.id,
            'discount_percentage': self.discount_percentage
        }
        if self.plan is not None and not nested:
            result['plan'] = self.plan.to_json(nested=True)
        if not nested:
            result['usage'] = self.subscriptions.all().count()
        if self.usage_limit:
            result['usage_limit'] = self.usage_limit
        return result

    def __str__(self):
        return "{0.identifier}: {0.discount_percentage}%".format(self)


class SubscriptionManager(models.Manager):

    def prepare_related(self):
        return self.select_related('payment', 'plan_description', 'plan_description__plan', 'discount', 'user')

    def is_active(self, user, subscription_type):
        if user is None:
            return False
        if user.id is None:
            return False
        if user.is_staff:
            return True
        return self.filter(user_id=user.id, plan_description__plan__type=subscription_type, expiration__gte=datetime.now()).count() > 0

    def subscribe(self, user, plan_description, discount_code, referral_user, return_url):
        if discount_code is not None:
            discount_code.is_valid(user, plan_description=plan_description, throw_exception=True)
        if referral_user is not None and referral_user.id == user.id:
            raise BadRequestException("The referral user can not be the same as the given subscriber.")
        price = plan_description.price if discount_code is None else discount_code.get_updated_price(plan_description.price)
        lang = get_current_request().LANGUAGE_CODE.split('-')[0].split('_')[0].upper()
        if lang not in {'CS', 'EN', 'DE'}:
            lang = 'EN'
        if price > 0:
            payment = Payment.objects.create_single_payment(
                order_number=str(uuid.uuid1()),
                order_description=plan_description.description,
                order_items={
                    plan_description.name: plan_description.price,
                },
                contact=Payment.objects.create_contact(email=user.email),
                currency=plan_description.currency,
                amount=price,
                return_url=return_url,
                lang=lang
            )
        else:
            payment = None

        subscription = Subscription(
            plan_description=plan_description,
            payment=payment,
            user=user,
            discount=discount_code,
            referral=referral_user
        )
        if payment is None:
            subscription.expiration = datetime.now() + relativedelta(months=subscription.plan_description.plan.months_validity)
        subscription.save()
        return subscription


class Subscription(models.Model):

    plan_description = models.ForeignKey(SubscriptionPlanDescription)
    payment = models.ForeignKey(Payment, null=True, blank=True)
    user = models.ForeignKey(User, related_name='subscriptions')
    expiration = models.DateTimeField(default=now)
    created = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session, null=True, blank=True, default=None)
    discount = models.ForeignKey(DiscountCode, null=True, blank=True, default=None, related_name='subscriptions')
    referral = models.ForeignKey(User, null=True, blank=True, default=None, related_name='referred_subscriptions')

    objects = SubscriptionManager()

    def is_active(self):
        return self.expiration > datetime.now()

    def to_json(self, nested=False, confidential=False):
        result = {
            'expiration': self.expiration.strftime('%Y-%m-%d %H:%M:%S'),
            'created': self.created.strftime('%Y-%m-%d %H:%M:%S'),
            'id': self.id,
            'object_type': 'subscription_subscription',
        }
        if nested:
            result['payment_id'] = self.payment_id
            result['plan_description_id'] = self.plan_description_id
            result['session_id'] = self.session_id
            result['user_id'] = self.user_id
        else:
            if not confidential:
                if self.payment is not None:
                    result['payment'] = {
                        'id': self.payment.id,
                        'object_type': 'payment',
                        'state': self.payment.state,
                        'status': self.payment.status,
                    }
                if self.discount is not None:
                    result['discount'] = self.discount.to_json(nested=True)
                if self.session is not None:
                    result['session'] = self.session.to_json(nested=True)
            result['plan_description'] = self.plan_description.to_json()
            result['user'] = {
                'id': self.user.id,
                'username': self.user.username
            }
        return result


@receiver(payment_changed)
def update_subcription_payment(sender, instance, previous_status, **kwargs):
    if previous_status['state'] == PaymentStatus.PAID or instance.state != PaymentStatus.PAID:
        return
    subscription = Subscription.objects.select_related('plan_description__plan').get(payment=instance)
    if subscription.plan_description.plan.months_referral and subscription.referral:
        referral_subscription = subscription.referral.subscriptions.filter(
            plan_description__plan__type=subscription.plan_description.plan.type
        ).order_by('-expiration').first()
        if referral_subscription is not None and subscription.plan_description.plan.months_referral:
            if referral_subscription.is_active():
                referral_subscription.expiration += relativedelta(months=subscription.plan_description.plan.months_referral)
            else:
                referral_subscription.expiration = datetime.now() + relativedelta(months=subscription.plan_description.plan.months_referral)
            referral_subscription.save()
    subscription.expiration = datetime.now() + relativedelta(months=subscription.plan_description.plan.months_validity)
    subscription.save()


@receiver(pre_save, sender=Subscription)
@disable_for_loaddata
def init_session(sender, instance, **kwargs):
    if instance.session_id is None:
        instance.session_id = Session.objects.get_current_session_id()
