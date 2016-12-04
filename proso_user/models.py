from collections import defaultdict
from contextlib import closing
from django.contrib.auth.models import User
from django.core.mail import get_connection, send_mail
from django.db import models
from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.db.models import Q
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from geoip import geolite2
from html2text import html2text
from ipware.ip import get_ip
from lazysignup.signals import converted
from proso.django.auth import is_user_lazy, convert_lazy_user, is_user_real, is_user_social, name_lazy_user
from proso.django.models import disable_for_loaddata
from proso.django.request import get_current_request
from proso.django.response import HttpError
from proso.rand import random_string
from proso_common.models import get_config
from smtplib import SMTPException
from social.apps.django_app.default.models import UserSocialAuth
import copy
import datetime
import hashlib
import hmac
import logging
import os
import user_agents

LOGGER = logging.getLogger('django.request')


def _load_user_id_from_GET(request, allow_override=False):
    if 'user' not in request.GET and 'username' not in request.GET:
        return None
    if 'user' in request.GET and request.user.is_staff:
        return int(request.GET['user'])
    if not allow_override:
        return None
    if 'user' in request.GET:
        profile = UserProfile.objects.filter(user_id=int(request.GET['user'])).first()
    else:
        profile = UserProfile.objects.filter(user__username=request.GET['username']).first()
    if profile is None:
        raise HttpError(404, _('There is no profile for the given user'), 'profile_not_found')
    if profile.public:
        return profile.user_id
    else:
        return None


def is_user_id_overridden(request, allow_override=False):
    return _load_user_id_from_GET(request, allow_override=allow_override) is not None


def get_user_id(request, allow_override=False):
    loaded_user_id = _load_user_id_from_GET(request, allow_override=allow_override)
    return request.user.id if loaded_user_id is None else loaded_user_id


def get_content_hash(content):
    return str(hashlib.sha1(content.encode()).hexdigest())


class UserProfileManager(models.Manager):

    def get_user_hash(self, user):
        return hmac.new(key=user.password.encode(), msg=str(user.id).encode()).hexdigest()


class UserProfile(models.Model):

    user = models.OneToOneField(User)
    send_emails = models.BooleanField(default=True)
    public = models.BooleanField(default=False)

    objects = UserProfileManager()

    def to_json(self, nested=False, stats=False):
        data = {
            'id': self.id,
            'object_type': 'user_profile',
            'send_emails': self.send_emails,
            'public': self.public,
            'properties': dict([
                (p.name, p.value) for p in
                UserProfileProperty.objects.filter(user_profile=self.id)]),
            'user': {
                'id': self.user.id,
                'object_type': 'auth_user',
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'username': self.user.username,
                'email': self.user.email,
                'staff': self.user.is_staff,
                'groups': [{
                    'id': g.id,
                    'object_type': 'auth_group',
                    'name': g.name,
                } for g in self.user.groups.all()]
            }
        }
        if not nested:
            data['member_of'] = [c.to_json(nested=True) for c in self.classes.all()]
            data['owner_of'] = [c.to_json(nested=True, members=True) for c in self.owned_classes.all()]
        if stats:
            from proso_models.models import Answer
            data["number_of_answers"] = Answer.objects.count(self.user)
            data["number_of_correct_answers"] = Answer.objects.correct_count(self.user)
        return data

    def __str__(self):
        return "Profile: '{0.user.username}'".format(self)

    def save_properties(self, properties_json):
        for property_dict in properties_json:
            property_dict['value'] = str(property_dict['value']).replace('+', ' ')
            try:
                property_object = UserProfileProperty.objects.get(
                    user_profile=self, name=property_dict['name'])
            except UserProfileProperty.DoesNotExist:
                property_object = UserProfileProperty(
                    user_profile=self, name=property_dict['name'])
            if property_object.value != property_dict['value']:
                property_object.value = property_dict['value']
                property_object.save()


class UserProfileProperty(models.Model):
    user_profile = models.ForeignKey(UserProfile, db_index=True)
    name = models.CharField(max_length=20, null=False, blank=False,
                            db_index=True)
    value = models.CharField(max_length=200, null=False)


class HttpUserAgentManager(models.Manager):

    def from_content(self, content):
        with transaction.atomic():
            try:
                content_hash = get_content_hash(content)
                return self.get(content_hash=content_hash)
            except HttpUserAgent.DoesNotExist:
                user_agent = user_agents.parse(content)
                http_user_agent = HttpUserAgent(
                    content=content,
                    content_hash=content_hash,
                    device_family=user_agent.device.family,
                    os_family=user_agent.os.family,
                    os_version=user_agent.os.version_string,
                    browser_family=user_agent.browser.family,
                    browser_version=user_agent.browser.version_string)
                http_user_agent.save()
                return http_user_agent


class HttpUserAgent(models.Model):

    content = models.TextField(null=False, blank=False)
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True, unique=True)
    device_family = models.CharField(max_length=50, null=True, blank=True, default=None)
    os_family = models.CharField(max_length=39, null=True, blank=True, default=None)
    os_version = models.CharField(max_length=39, null=True, blank=True, default=None)
    browser_family = models.CharField(max_length=39, null=True, blank=True, default=None)
    browser_version = models.CharField(max_length=39, null=True, blank=True, default=None)

    objects = HttpUserAgentManager()

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'http_user_agent',
            'content': self.content,
            'os_family': self.os_family,
            'os_version': self.os_version,
            'browser_family': self.browser_family,
            'browser_version': self.browser_version,
            'device_family': self.device_family
        }

    def __str__(self):
        return ("{0.os_family} - {0.os_version} - {0.browser_family}" +
                "- {0.browser_version} - {0.device_family}").format(self)


class TimeZoneManager(models.Manager):

    def from_content(self, content):
        with transaction.atomic():
            try:
                content_hash = get_content_hash(content)
                return self.get(content_hash=content_hash)
            except TimeZone.DoesNotExist:
                time_zone = TimeZone(content=content, content_hash=content_hash)
                time_zone.save()
                return time_zone


class LocationManager(models.Manager):

    def from_ip_address(self, ip_address):
        try:
            return self.get(ip_address=ip_address)
        except Location.DoesNotExist:
            location = Location(ip_address=ip_address)
            location.save()
            return location


class Location(models.Model):

    ip_address = models.CharField(max_length=39, null=True, blank=True, default=None, unique=True)

    objects = LocationManager()

    def to_json(self, nested=False):
        result = {
            'id': self.id,
            'object_type': 'location',
            'ip_address': self.ip_address
        }
        country = self.get_country()
        if country is not None:
            result['country'] = country
        return result

    def get_country(self):
        if self.ip_address is None or self.ip_address.startswith('127.0'):
            return None
        match = geolite2.lookup(self.ip_address)
        return None if match is None else match.country

    def __str__(self):
        return self.ip_address


class TimeZone(models.Model):

    content = models.TextField(null=False, blank=False)
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True, unique=True)

    objects = TimeZoneManager()

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'time_zone',
            'content': self.content
        }

    def __str__(self):
        return self.content


class SessionManager(models.Manager):

    def get_current_session(self):
        session_id = self.get_current_session_id()
        if session_id is None:
            return None
        return self.get(id=session_id)

    def get_current_session_id(self):
        current_request = get_current_request(force=False)
        if current_request is None:
            return None
        session_id = current_request.session.get('proso_user_current_session_id')
        session_last_touch = current_request.session.get('proso_user_current_session_last_touch')
        session_last_touch = datetime.datetime.strptime(session_last_touch, '%Y-%m-%d %H:%M:%S') if session_last_touch else None
        if session_id is None or (datetime.datetime.now() - session_last_touch).total_seconds() > 15 * 60:
            current_session = Session(user_id=current_request.user.id)
            current_session.save()
            current_request.session['proso_user_current_session_id'] = current_session.id
        current_request.session['proso_user_current_session_last_touch'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return int(current_request.session.get('proso_user_current_session_id'))

    def reset_current_session(self):
        current_request = get_current_request(force=False)
        if current_request is None:
            return
        if 'proso_user_current_session_id' not in current_request.session:
            return
        del current_request.sesion['proso_user_current_session_id']
        del current_request.session['proso_user_current_session_last_touch']


class Session(models.Model):

    user = models.ForeignKey(User)
    time_zone = models.ForeignKey(TimeZone, null=True, blank=True, default=None)
    http_user_agent = models.ForeignKey(HttpUserAgent, null=True, blank=True, default=None)
    location = models.ForeignKey(Location, null=True, blank=True, default=None)
    locale = models.CharField(max_length=50, null=True, blank=True, default=None)
    display_width = models.IntegerField(null=True, blank=True, default=None)
    display_height = models.IntegerField(null=True, blank=True, default=None)

    objects = SessionManager()

    def to_json(self, nested=False):
        result = {
            'object_type': 'session',
            'id': self.id,
            'user_id': self.user_id,
            'locale': self.locale,
            'display_width': self.display_width,
            'display_height': self.display_height
        }
        if self.time_zone:
            result['time_zone'] = self.time_zone.to_json(nested=True)
        if self.location:
            result['location'] = self.location.to_json(nested=True)
        if self.http_user_agent:
            result['http_user_agent'] = self.http_user_agent.to_json(nested=True)
        return result


class ScheduledEmailManager(models.Manager):

    def schedule_more(self, from_email, subject, template_file, users=None, emails=None, skip_emails=None, langs=None, output_dir=None, dry=False, active_from=None, template_kwargs=None, scheduled=None):
        from proso_models.models import Answer
        if users is not None and emails is not None:
            raise Exception('Both users and e-mails can not be specified.')
        if template_kwargs is None:
            template_kwargs = {}
        if emails is not None:
            users = User.objects.filter(email__in=emails)
        elif users is None:
            users = User.objects.filter(Q(email__isnull=False) & ~Q(email=''))
        if skip_emails is not None:
            users = users.exclude(email__in=skip_emails)
        users = list(users)
        user_ids = [user.id for user in users]
        if langs is not None:
            valid_users = set(Answer.objects.filter(lang__in=langs, user_id__in=user_ids).distinct('user_id').values_list('user_id', flat=True))
            users = [u for u in users if u.id in valid_users]
            user_ids = list(valid_users & set(user_ids))
        if active_from is not None:
            if isinstance(active_from, str):
                active_from = datetime.datetime.strptime(active_from, '%Y-%m-%d')
            valid_users = set(Answer.objects.filter(time__gte=active_from).values_list('user_id', flat=True))
            users = [u for u in users if u.id in valid_users]
            user_ids = list(valid_users & set(user_ids))
        send_emails = dict(UserProfile.objects.filter(user_id__in=user_ids).values_list('user_id', 'send_emails'))
        result = []
        for user in users:
            if not send_emails.get(user.id, False):
                continue
            user_template_kwargs = copy.deepcopy(template_kwargs)
            user_template_kwargs['user'] = user
            user_template_kwargs['token'] = UserProfile.objects.get_user_hash(user)
            user_template_kwargs['subject'] = subject
            msg_html = render_to_string(template_file, user_template_kwargs)
            if output_dir:
                filename = os.path.join(output_dir, '{}_{}.html'.format(slugify(subject), user.email))
                with open(filename, 'w') as f:
                    print('Creating {}'.format(filename))
                    f.write(msg_html)
            msg_plain = html2text(msg_html)
            if not dry:
                self.schedule(user, subject, msg_plain, from_email, html_message=msg_html, scheduled=scheduled)
            result.append(user)
        return result

    def schedule(self, user, subject, message, from_email, scheduled=None, html_message=None):
        self.create(
            user=user,
            subject=subject,
            message=message,
            from_email=from_email,
            scheduled=datetime.datetime.now() if scheduled is None else scheduled,
            html_message=html_message,
            status=ScheduledEmail.STATUS_SCHEDULED
        )

    def send(self, n=100, auth_user=None, auth_password=None):
        emails = list(self.select_related('user').filter(status=ScheduledEmail.STATUS_SCHEDULED, scheduled__lt=datetime.datetime.now() + datetime.timedelta(minutes=121)).order_by('-scheduled')[:n])
        user_ids = [e.user_id for e in emails]
        send_emails = dict(UserProfile.objects.filter(user_id__in=user_ids).values_list('user_id', 'send_emails'))
        with closing(get_connection(username=auth_user, password=auth_password)) as connection:
            for email in emails:
                if not send_emails[email.user_id]:
                    email.status = ScheduledEmail.STATUS_SKIPPED
                    email.save()
                    continue
                try:
                    send_mail(
                        email.subject,
                        email.message,
                        email.from_email,
                        [email.user.email],
                        connection=connection,
                        html_message=email.html_message
                    )
                    email.status = ScheduledEmail.STATUS_SENT
                except SMTPException:
                    LOGGER.exception('There is an error during sending a scheduled email.')
                    email.status = ScheduledEmail.STATUS_FAILED
                email.save()


class ScheduledEmail(models.Model):

    STATUS_SCHEDULED = 0
    STATUS_SENT = 1
    STATUS_SKIPPED = 2
    STATUS_FAILED = 3

    STATUS = (
        (STATUS_SCHEDULED, 'scheduled'),
        (STATUS_SENT, 'sent'),
        (STATUS_SKIPPED, 'skipped'),
        (STATUS_FAILED, 'failed'),
    )

    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    scheduled = models.DateTimeField()
    processed = models.DateTimeField(auto_now=True)
    status = models.PositiveSmallIntegerField(choices=STATUS)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    html_message = models.TextField(default=None, null=True, blank=True)
    from_email = models.CharField(max_length=255)

    objects = ScheduledEmailManager()

    def to_json(self, nested=False):
        return {
            'created': self.created.strftime('%Y-%m-%d %H:%M:%S'),
            'scheduled': self.scheduled.strftime('%Y-%m-%d %H:%M:%S'),
            'processed': self.processed.strftime('%Y-%m-%d %H:%M:%S'),
            'object_type': 'scheduled_email',
            'status': dict(ScheduledEmail.STATUS)[self.status],
            'subject': self.subject,
            'message': self.message,
            'html_message': self.html_message,

        }


class UserQuestionEventManager(models.Manager):

    def from_type_value(self, type, value):
        result = self.filter(type=type, value=value).first()
        if result is None:
            result = UserQuestionEvent(type=type, value=value)
            result.save()
        return result


class UserQuestionEvent(models.Model):

    type = models.CharField(max_length=50, null=False, blank=False)
    value = models.CharField(max_length=50, null=False, blank=False)

    objects = UserQuestionEventManager()

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'user_question_event',
            'type': self.type,
            'value': self.value,
        }


class UserQuestionConditionManager(models.Manager):

    def from_type_value(self, type, value):
        result = self.filter(type=type, value=value).first()
        if result is None:
            result = UserQuestionCondition(type=type, value=value)
            result.save()
        return result


class UserQuestionCondition(models.Model):

    type = models.CharField(max_length=50, null=False, blank=False)
    value = models.CharField(max_length=50, null=False, blank=False)

    objects = UserQuestionConditionManager()

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'user_question_condition',
            'type': self.type,
            'value': self.value,
        }


class UserQuestionManager(models.Manager):

    def questions_to_ask(self, user_id, language):
        user_answers = defaultdict(list)
        for user_answer in UserQuestionAnswer.objects.select_related('question').filter(user_id=user_id):
            user_answers[user_answer.question.identifier].append(user_answer)
        questions = self.prefetch_related(
            'possible_answers', 'on_events', 'conditions'
        ).filter(active=True, lang=language).exclude(identifier__in=list(user_answers.keys()), repeat=False)
        return questions


class UserQuestion(models.Model):

    TYPE_OPEN = 'o'
    TYPE_CLOSED = 'c'
    TYPE_MIXED = 'm'

    ANSWER_TYPES = (
        (TYPE_CLOSED, 'closed'),
        (TYPE_MIXED, 'mixed'),
        (TYPE_OPEN, 'open'),
    )

    identifier = models.SlugField()
    lang = models.CharField(max_length=10, null=False, blank=False)
    content = models.TextField(null=False, blank=False)
    active = models.BooleanField(null=False, blank=False, default=True)
    answer_type = models.CharField(choices=ANSWER_TYPES, default='o', max_length=1)
    on_events = models.ManyToManyField(UserQuestionEvent)
    conditions = models.ManyToManyField(UserQuestionCondition)
    repeat = models.BooleanField(default=False)

    objects = UserQuestionManager()

    def to_json(self, nested=False):
        result = {
            'id': self.id,
            'identifier': self.identifier,
            'object_type': 'user_question',
            'lang': self.lang,
            'content': self.content,
            'active': self.active,
            'answer_type': self.answer_type,
            'on_events': [e.to_json(nested=True) for e in self.on_events.all()],
            'conditions': [c.to_json(nested=True) for c in self.conditions.all()],
            'repeat': self.repeat,
        }
        if not nested:
            result['possible_answers'] = []
            for possible_answer in self.possible_answers.all():
                if possible_answer.active:
                    result['possible_answers'].append(possible_answer.to_json(nested=True))
        return result


class UserQuestionPossibleAnswer(models.Model):

    identifier = models.SlugField()
    active = models.BooleanField(null=False, blank=False, default=True)
    content = models.CharField(max_length=100, null=False, blank=False)
    question = models.ForeignKey(UserQuestion, null=False, blank=False, related_name='possible_answers')

    def to_json(self, nested=False):
        result = {
            'id': self.id,
            'identifier': self.identifier,
            'object_type': 'user_question_possible_answer',
            'content': self.content,
        }
        if not nested:
            result['question'] = self.question.to_json(nested=True)
        return result


class UserQuestionAnswer(models.Model):

    user = models.ForeignKey(User)
    closed_answer = models.ForeignKey(UserQuestionPossibleAnswer, null=True, blank=True, default=True)
    open_answer = models.CharField(max_length=100, null=True, blank=True, default=None)
    time = models.DateTimeField(auto_now_add=True)
    question = models.ForeignKey(UserQuestion, related_name='user_answers')

    def to_json(self, nested=False):
        result = {
            'id': self.id,
            'object_type': 'user_question_answer',
        }
        if self.closed_answer is not None:
            result['closed_answer'] = self.closed_answer.to_json(nested=True)
        else:
            result['open_answer'] = self.open_answer
        if not nested:
            result['question'] = self.question.to_json(nested=True)
        return result


def migrate_google_openid_user(user):
    with transaction.atomic():
        if user and is_user_lazy(user):
            return None
        try:
            new_social = UserSocialAuth.objects.get(user_id=user.id, provider='google-oauth2')
        except UserSocialAuth.DoesNotExist:
            return None
        try:
            old_social = UserSocialAuth.objects.get(uid=user.email, provider='google')
            new_user = new_social.user
            new_social.user = old_social.user
            new_social.save()
            # in case of already migrated users do not lose data
            if new_user.id != old_social.user.id:
                new_user.delete()
            old_social.delete()
            LOGGER.info('Migrating user "{}" from Google OpenID to OAauth2'.format(user.email))
            return old_social.user
        except UserSocialAuth.DoesNotExist:
            return None


class ClassManager(models.Manager):

    def prepare_related(self):
        return self.select_related('owner').prefetch_related('members')


class Class(models.Model):
    code = models.CharField(max_length=50, blank=True, unique=True)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(UserProfile, related_name='owned_classes')
    members = models.ManyToManyField(UserProfile, related_name='classes', blank=True)

    objects = ClassManager()

    class Meta:
        verbose_name_plural = 'classes'

    def to_json(self, nested=False, members=False):
        data = {
            'code': self.code,
            'name': self.name,
            'id': self.pk,
            'object_type': 'user_class',
        }

        data['owner'] = self.owner.to_json(nested=True)
        if not nested or members:
            data['members'] = [m.to_json(nested=True) for m in self.members.all()]

        return data

    def __str__(self):
        return self.name


################################################################################
# Signals
################################################################################

def init_content_hash(instance):
    if instance.content is not None and instance.content_hash is None:
        instance.content_hash = get_content_hash(instance.content)


@receiver(pre_save, sender=Session)
@disable_for_loaddata
def init_session_location(sender, instance, **kwargs):
    if instance.location is None:
        current_request = get_current_request(force=False)
        ip_address = get_ip(current_request) if current_request else None
        if ip_address:
            instance.location = Location.objects.from_ip_address(ip_address)


@receiver(pre_save, sender=Session)
@disable_for_loaddata
def init_session_http_user_agent(sender, instance, **kwargs):
    if instance.http_user_agent is None:
        current_request = get_current_request(force=False)
        if current_request:
            instance.http_user_agent = HttpUserAgent.objects.from_content(current_request.META.get('HTTP_USER_AGENT', ''))


@receiver(pre_save, sender=HttpUserAgent)
@disable_for_loaddata
def init_content_hash_http_user_agent(sender, instance, **kwargs):
    init_content_hash(instance)


@receiver(pre_save, sender=TimeZone)
@disable_for_loaddata
def init_content_hash_time_zone(sender, instance, **kwargs):
    init_content_hash(instance)


@receiver(pre_save, sender=User)
@disable_for_loaddata
def drop_lazy_user(sender, instance, created=False, **kwargs):
    if is_user_real(instance) and is_user_lazy(instance):
        convert_lazy_user(instance)


@receiver(post_save, sender=User)
@disable_for_loaddata
def init_user_profile(sender, instance, created=False, **kwargs):
    if is_user_real(instance) and not is_user_lazy(instance):
        UserProfile.objects.get_or_create(user=instance)


@receiver(converted)
@disable_for_loaddata
def init_username(sender, user, **kwargs):
    if is_user_social(user):
        name_lazy_user(user, save=False)


@receiver(pre_save, sender=Class)
def create_class_code(sender, instance, created=False, **kwargs):
    if not instance.code:
        condition = True
        while condition:
            code = random_string(get_config('proso_user', 'generated_code_length', default=5))
            condition = Class.objects.filter(code=code).exists()
        instance.code = code


PROSO_MODELS_TO_EXPORT = [
    User, UserProfile, Session, Location, HttpUserAgent, TimeZone,
    UserQuestionEvent, UserQuestionCondition, UserQuestion, UserQuestionAnswer,
    UserQuestionPossibleAnswer
]

PROSO_CUSTOM_EXPORT = {
    'session': '''
        SELECT
            proso_user_session.id,
            user_id,
            ip_address
        FROM proso_user_session
        INNER JOIN proso_user_location
            ON location_id = proso_user_location.id
    ''',
}
