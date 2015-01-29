from django.db import models
import hashlib
from ipware.ip import get_ip
import user_agents
from proso_common.models import get_current_request
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
import datetime


def get_content_hash(content):
    return hashlib.sha1(content).hexdigest()


class HttpUserAgentManager(models.Manager):

    def from_content(self, content):
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
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True)
    device_family = models.CharField(max_length=50, null=True, blank=True, default=None)
    os_family = models.CharField(max_length=39, null=True, blank=True, default=None)
    os_version = models.CharField(max_length=39, null=True, blank=True, default=None)
    browser_family = models.CharField(max_length=39, null=True, blank=True, default=None)
    browser_version = models.CharField(max_length=39, null=True, blank=True, default=None)

    objects = HttpUserAgentManager()


class TimeZoneManager(models.Manager):

    def from_content(self, content):
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


class TimeZone(models.Model):

    content = models.TextField(null=False, blank=False)
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True)

    objects = TimeZoneManager()


class SessionManager(models.Manager):

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


################################################################################
# Signals
################################################################################

def init_content_hash(instance):
    if instance.content is not None and instance.content_hash is None:
        instance.content_hash = get_content_hash(instance.content)


@receiver(pre_save, sender=Session)
def init_session_location(sender, instance, **kwargs):
    if instance.location is None:
        current_request = get_current_request(force=False)
        ip_address = get_ip(current_request) if current_request else None
        if ip_address:
            instance.location = Location.objects.from_ip_address(ip_address)


@receiver(pre_save, sender=Session)
def init_session_http_user_agent(sender, instance, **kwargs):
    if instance.http_user_agent is None:
        current_request = get_current_request(force=False)
        if current_request:
            instance.http_user_agent = HttpUserAgent.objects.from_content(current_request.META.get('HTTP_USER_AGENT', ''))


@receiver(pre_save, sender=HttpUserAgent)
def init_content_hash_http_user_agent(sender, instance, **kwargs):
    init_content_hash(instance)


@receiver(pre_save, sender=TimeZone)
def init_content_hash_time_zone(sender, instance, **kwargs):
    init_content_hash(instance)
