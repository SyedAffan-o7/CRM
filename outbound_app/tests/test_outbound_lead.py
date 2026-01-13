from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory

from outbound_app.models import OutboundActivity
from outbound_app.admin import OutboundActivityAdmin


class TestOutboundLeadIntegration(SimpleTestCase):
    def test_model_has_lead_field(self):
        field_names = [f.name for f in OutboundActivity._meta.get_fields()]
        self.assertIn('lead', field_names)

    def test_admin_shows_lead(self):
        # Ensure 'lead' is configured in list_display and autocomplete_fields
        self.assertIn('lead', OutboundActivityAdmin.list_display)
        self.assertIn('lead', OutboundActivityAdmin.autocomplete_fields)

    @patch('leads_app.views.render')
    @patch('leads_app.views.OutboundActivity')
    @patch('leads_app.views.get_object_or_404')
    def test_lead_detail_includes_outbound_activities(self, mock_get_obj, mock_oa, mock_render):
        # Arrange: mock lead and queryset
        mock_lead = SimpleNamespace(id=1, assigned_sales_person=None)
        mock_get_obj.return_value = mock_lead

        # Mock queryset chain: select_related(...).filter(...).order_by(...)
        mock_qs = [SimpleNamespace(id=11), SimpleNamespace(id=12)]
        mock_manager = MagicMock()
        mock_manager.select_related.return_value.filter.return_value.order_by.return_value = mock_qs
        mock_oa.objects = mock_manager

        # Mock render to capture context
        def fake_render(request, template, context):
            # Assert
            assert 'outbound_activities' in context
            assert context['outbound_activities'] == mock_qs
            return HttpResponse('ok')

        mock_render.side_effect = fake_render

        # Act: call the view with a superuser to bypass permission
        from leads_app.views import lead_detail

        rf = RequestFactory()
        request = rf.get('/enquiries/1/')
        request.user = SimpleNamespace(is_superuser=True)

        response = lead_detail(request, pk=1)

        # Assert: received response from fake_render
        self.assertEqual(response.status_code, 200)
