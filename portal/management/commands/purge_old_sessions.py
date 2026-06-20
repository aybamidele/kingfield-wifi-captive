from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from portal.models import GuestWifiSession


class Command(BaseCommand):
    help = "Delete old guest Wi-Fi sessions after the retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many sessions would be deleted without deleting.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Retention period in days. Defaults to DATA_RETENTION_DAYS.",
        )

    def handle(self, *args, **options):
        days = options["days"] or settings.DATA_RETENTION_DAYS
        cutoff = timezone.now() - timedelta(days=days)
        queryset = GuestWifiSession.objects.filter(created_at__lt=cutoff)
        count = queryset.count()

        if options["dry_run"]:
            self.stdout.write(f"{count} session(s) would be deleted.")
            return

        queryset.delete()
        self.stdout.write(f"Deleted {count} old guest Wi-Fi session(s).")
