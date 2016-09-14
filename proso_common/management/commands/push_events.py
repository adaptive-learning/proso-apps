from django.core.management.base import BaseCommand
from proso_common.models import get_events_pusher


class Command(BaseCommand):
    help = 'Push all events from events.log'

    def handle(self, *args, **options):
        pusher = get_events_pusher()

        pusher.push_all()
        self.stdout.write(self.style.SUCCESS('Successfully sent events.'))
