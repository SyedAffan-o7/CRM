from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OutboundActivity
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OutboundActivity)
def update_contact_on_activity(sender, instance: OutboundActivity, created: bool, **kwargs):
    if not created:
        return
    try:
        contact = instance.contact
        if not contact:
            return
        # Respect manual override
        if hasattr(contact, 'manual_status_override') and getattr(contact, 'manual_status_override', False):
            return

        update_fields = []

        # last_contacted
        if hasattr(contact, 'last_contacted'):
            contact.last_contacted = instance.created_at
            update_fields.append('last_contacted')

        # outbound_status
        if hasattr(contact, 'outbound_status'):
            new_status = 'CONTACTED'
            try:
                if instance.lead is not None:
                    # If a lead is associated, consider converted
                    new_status = 'CONVERTED'
            except Exception:
                pass
            contact.outbound_status = new_status
            update_fields.append('outbound_status')

        if update_fields:
            contact.save(update_fields=update_fields)
    except Exception as e:
        logger.warning("OutboundActivity post_save failed to update contact: %s", e)
