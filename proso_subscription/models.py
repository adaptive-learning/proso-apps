from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver
from gopay.enums import PaymentStatus
from gopay_django_api.models import Payment
from gopay_django_api.signals import payment_changed
import uuid


class SubscriptionPlanManager(models.Manager):

    def prepare_related(self):
        return self.prefetch_related('descriptions')


class SubscriptionPlan(models.Model):

    identifier = models.SlugField()
    months_validity = models.IntegerField()
    type = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    objects = SubscriptionPlanManager()

    def to_json(self, nested=False):
        result = {
            'identifier': self.identifier,
            'id': self.id,
            'object_type': 'subscription_plan',
            'type': self.type,
            'active': self.active,
            'months-validity': self.months_validity,
        }
        if not nested:
            result['descriptions'] = [d.to_json(nested=True) for d in self.descriptions.all()]
        return result


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

    def to_json(self, nested=False):
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
        return result


class SubscriptionManager(models.Manager):

    def prepare_related(self):
        return self.select_related('payment', 'plan_description', 'plan_description__plan')

    def subscribe(self, user, plan_description, return_url):
        payment = Payment.objects.create_single_payment(
            Payment.objects.create_contact(email=user.email),
            order_number=str(uuid.uuid1()),
            order_description=plan_description.description,
            order_items={
                plan_description.name: plan_description.price,
            },
            currency=plan_description.currency,
            amount=plan_description.price,
            return_url=return_url
        )
        return self.create(
            plan_description=plan_description,
            payment=payment,
            user=user
        )


class Subscription(models.Model):

    plan_description = models.ForeignKey(SubscriptionPlanDescription)
    payment = models.ForeignKey(Payment)
    user = models.ForeignKey(User)
    expiration = models.DateTimeField(auto_now_add=True)
    created = models.DateTimeField(auto_now_add=True)

    objects = SubscriptionManager()

    def to_json(self, nested=False):
        result = {
            'expiration': self.expiration.strftime('%Y-%m-%d %H:%M:%S'),
            'created': self.created.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id,
            'id': self.id,
            'object_type': 'subscription_subscription',
        }
        if nested:
            result['payment_id'] = self.payment_id
            result['plan_description_id'] = self.plan_description_id
        else:
            result['payment'] = {
                'id': self.payment.id,
                'object_type': 'payment',
                'state': self.payment.state,
                'status': self.payment.status,
            }
            result['plan_description'] = self.plan_description.to_json()
        return result


@receiver(payment_changed)
def update_subcription_payment(sender, instance, previous_status, **kwargs):
    if previous_status['state'] == PaymentStatus.PAID or instance.state != PaymentStatus.PAID:
        return
    subscription = Subscription.objects.select_related('plan_description__plan').get(payment=instance)
    subscription.expiration = datetime.now() + relativedelta(months=subscription.plan_description.plan.months_validity)
    subscription.save()
