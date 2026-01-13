from django.test import TestCase, override_settings
from django.db import connection
from django.contrib.auth import get_user_model
from outbound_app.models import OutboundActivity, Campaign

try:
    from customers_app.models import Contact
except Exception:  # pragma: no cover
    Contact = None


class OutboundActivityModelTests(TestCase):
    def setUp(self):
        # Skip tests if legacy contact table is not available (managed=False model)
        if Contact is None:
            self.skipTest("customers_app.Contact not importable")
        tables = connection.introspection.table_names()
        if 'crm_app_contact' not in tables:
            self.skipTest("crm_app_contact table not present in test database")

        # Ensure there is at least one Campaign and User
        self.campaign = Campaign.objects.create(name="Test Campaign")
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='testpass')

        # Create a minimal Contact record (expects legacy table with required columns)
        self.contact = Contact.objects.create(
            full_name='John Doe',
            phone_number='1234567890',
        )

    def test_create_outbound_activity_creates_record(self):
        count_before = OutboundActivity.objects.count()
        OutboundActivity.objects.create(
            campaign=self.campaign,
            contact=self.contact,
            method='PHONE',
            summary='Called customer',
            created_by=self.user,
        )
        self.assertEqual(OutboundActivity.objects.count(), count_before + 1)

    def test_signal_updates_contact_last_contacted_and_status(self):
        # If manual_status_override=True then signal should not change status
        if hasattr(self.contact, 'manual_status_override'):
            self.contact.manual_status_override = False
            self.contact.save(update_fields=['manual_status_override'])

        act = OutboundActivity.objects.create(
            campaign=self.campaign,
            contact=self.contact,
            method='PHONE',
            summary='Follow-up call',
            created_by=self.user,
        )
        # Refresh from DB
        refreshed = Contact.objects.get(pk=self.contact.pk)
        if hasattr(refreshed, 'last_contacted'):
            self.assertIsNotNone(refreshed.last_contacted)
        if hasattr(refreshed, 'outbound_status'):
            self.assertEqual(refreshed.outbound_status, 'CONTACTED')

        # Now set manual override and ensure no change on next activity
        if hasattr(refreshed, 'manual_status_override'):
            refreshed.manual_status_override = True
            refreshed.save(update_fields=['manual_status_override'])
            OutboundActivity.objects.create(
                campaign=self.campaign,
                contact=refreshed,
                method='EMAIL',
                summary='Sent email',
                created_by=self.user,
            )
            refreshed2 = Contact.objects.get(pk=refreshed.pk)
            if hasattr(refreshed2, 'outbound_status'):
                # Should remain whatever it was before manual override
                self.assertEqual(refreshed2.outbound_status, refreshed.outbound_status)
