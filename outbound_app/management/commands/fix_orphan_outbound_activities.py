from django.core.management.base import BaseCommand
from django.db.models import F
from django.db import transaction

from outbound_app.models import OutboundActivity
from customers_app.models import Contact
try:
    from leads_app.models import Lead
except Exception:
    Lead = None


class Command(BaseCommand):
    help = (
        "Find and optionally delete OutboundActivity rows whose contact_id/lead_id "
        "do not exist in the corresponding legacy tables. This resolves foreign key "
        "integrity errors during migrations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually delete orphan rows. Without this flag, performs a dry run.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Preview up to N orphan rows per category (default: 20).",
        )

    def handle(self, *args, **options):
        # Django exposes arguments without the dashes in the options dict
        apply = options.get("apply", False)
        limit = options.get("limit", 20)

        # Style fallbacks for broader Django compatibility
        heading_style = getattr(self.style, 'MIGRATE_HEADING', self.style.SUCCESS)
        notice_style = getattr(self.style, 'NOTICE', self.style.WARNING)

        self.stdout.write(heading_style("Scanning for orphan OutboundActivity rows..."))

        # Orphan by contact
        existing_contact_ids = Contact.objects.values_list("id", flat=True)
        orphans_by_contact = (
            OutboundActivity.objects
            .exclude(contact_id__isnull=True)
            .exclude(contact_id__in=existing_contact_ids)
        )
        count_contact = orphans_by_contact.count()

        # Orphan by lead (optional if Lead unavailable)
        count_lead = 0
        orphans_by_lead = OutboundActivity.objects.none()
        if Lead is not None:
            existing_lead_ids = Lead.objects.values_list("id", flat=True)
            orphans_by_lead = (
                OutboundActivity.objects
                .exclude(lead_id__isnull=True)
                .exclude(lead_id__in=existing_lead_ids)
            )
            count_lead = orphans_by_lead.count()

        total_orphans = count_contact + count_lead
        self.stdout.write(f"Orphans by contact: {count_contact}")
        self.stdout.write(f"Orphans by lead:    {count_lead}")
        self.stdout.write(self.style.WARNING(f"Total orphan rows: {total_orphans}"))

        # Preview
        if count_contact:
            self.stdout.write("\nSample orphan rows by contact:")
            for row in orphans_by_contact.values("id", "contact_id")[:limit]:
                self.stdout.write(f"  id={row['id']} contact_id={row['contact_id']}")
        if count_lead:
            self.stdout.write("\nSample orphan rows by lead:")
            for row in orphans_by_lead.values("id", "lead_id")[:limit]:
                self.stdout.write(f"  id={row['id']} lead_id={row['lead_id']}")

        if not total_orphans:
            self.stdout.write(self.style.SUCCESS("No orphan rows found. Nothing to do."))
            return

        if not apply:
            self.stdout.write(notice_style("\nDry run complete. Re-run with --apply to delete the orphan rows."))
            return

        # Apply deletion
        with transaction.atomic():
            ids_to_delete = list(orphans_by_contact.values_list("id", flat=True))
            ids_to_delete += list(orphans_by_lead.values_list("id", flat=True))
            if ids_to_delete:
                deleted, _ = OutboundActivity.objects.filter(id__in=ids_to_delete).delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} orphan OutboundActivity rows."))
            else:
                self.stdout.write("No rows to delete.")

        self.stdout.write(self.style.SUCCESS("Cleanup complete. You can now run migrations."))
