from django.core.management.base import BaseCommand, CommandError
from proso_common.models import get_events_logger, get_events_pusher, get_events_client


class Command(BaseCommand):
    help = 'Push all events from events.log'

    def handle(self, *args, **options):
        pusher = get_events_pusher()

        pusher.push_all()
        self.stdout.write(self.style.SUCCESS('Successfully sent events.'))
