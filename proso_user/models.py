from django.db import models
import hashlib
from ipware.ip import get_ip
import user_agents
from social.apps.django_app.default.models import UserSocialAuth
from proso.django.request import get_current_request
from django.db.models.signals import pre_save, post_save
from lazysignup.signals import converted
from django.dispatch import receiver
from django.contrib.auth.models import User
import datetime
from proso.django.auth import is_user_lazy, convert_lazy_user, is_user_real, is_user_social, name_lazy_user
from proso.django.util import disable_for_loaddata
from django.db import transaction
from collections import defaultdict
from proso.django.response import HttpError
from django.utils.translation import ugettext as _
import logging


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
        raise HttpError(404, _('There is no profile for the given user'))
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
    return hashlib.sha1(content.encode()).hexdigest()


class UserProfile(models.Model):

    user = models.OneToOneField(User)
    send_emails = models.BooleanField(default=True)
    public = models.BooleanField(default=False)

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
                'object_type': 'user',
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'username': self.user.username,
                'email': self.user.email,
                'staff': self.user.is_staff,
            }
        }
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
        return {
            'id': self.id,
            'object_type': 'location',
            'ip_address': self.ip_address
        }

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
