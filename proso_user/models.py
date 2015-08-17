from django.db import models
import hashlib
from ipware.ip import get_ip
import user_agents
from proso.django.request import get_current_request
from django.db.models.signals import pre_save, post_save
from lazysignup.signals import converted
from django.dispatch import receiver
from django.contrib.auth.models import User
import datetime
from proso.django.auth import is_user_lazy, convert_lazy_user, is_user_real, is_user_social, name_lazy_user
from proso.django.util import disable_for_loaddata
from django.db import transaction
from social_auth.models import UserSocialAuth
import logging


LOGGER = logging.getLogger('django.request')


def get_content_hash(content):
    return hashlib.sha1(content).hexdigest()


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

    ip_address = models.CharField(max_length=39, null=True, blank=True, default=None)

    objects = LocationManager()

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'location',
            'ip_address': self.ip_address
        }


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


PROSO_MODELS_TO_EXPORT = [User, UserProfile, Session]
