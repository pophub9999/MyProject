import sqlite3,tarfile
from pathlib import Path
from datetime import datetime,timezone
from django.conf import settings
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help="Create a consistent database snapshot and media archive."
    def handle(self,*args,**kwargs):
        folder=Path("/data/backups")/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder.mkdir(parents=True,mode=0o700)
        with sqlite3.connect(settings.DATABASES["default"]["NAME"]) as source:
            with sqlite3.connect(folder/"store.sqlite3") as target: source.backup(target)
        with tarfile.open(folder/"media.tar.gz","w:gz") as archive: archive.add(settings.MEDIA_ROOT,arcname="media")
        self.stdout.write(str(folder))
