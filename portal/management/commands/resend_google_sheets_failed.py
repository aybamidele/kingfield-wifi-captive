from django.core.management.base import BaseCommand

from portal.models import GuestWifiSession
from portal.services import google_sheets


class Command(BaseCommand):
    help = "Retry failed Google Sheets webhook posts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many failed sessions would be retried without sending.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of failed sessions to retry.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        sessions = list(
            GuestWifiSession.objects.filter(
                google_sheets_status=GuestWifiSession.GoogleSheetsStatus.FAILED
            ).order_by("created_at")[:limit]
        )

        if options["dry_run"]:
            count = len(sessions)
            noun = "session" if count == 1 else "sessions"
            self.stdout.write(
                f"{count} failed Google Sheets {noun} would be retried."
            )
            return

        for session in sessions:
            google_sheets.send_session_to_google_sheets(session)

        self.stdout.write(
            f"Retried {len(sessions)} failed Google Sheets session(s)."
        )
