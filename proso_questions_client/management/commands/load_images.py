from django.core.management.base import BaseCommand, CommandError
import os
import shutil


class Command(BaseCommand):
    help = u"""Load files to static folder."""

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError(
                "Not enough arguments. One argument required: " +
                " <folder> folder containing the files")
        dirpath = args[0]
        for filename in os.listdir(dirpath):
            print 'copying', os.path.join(dirpath, filename), 'to', "./proso_questions_client/static/dist/"
            shutil.copy2(os.path.join(dirpath, filename), "./proso_questions_client/static/dist/")
