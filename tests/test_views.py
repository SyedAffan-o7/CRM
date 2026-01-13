import pytest
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_dashboard_view():
    """Test that dashboard loads for authenticated user"""
    # Create test user
    user = User.objects.create_user('testuser', 'test@example.com', 'testpass')
    user.is_superuser = True
    user.save()

    # Create client and login
    client = Client()
    client.login(username='testuser', password='testpass')

    # Test dashboard
    response = client.get('/dashboard/')
    assert response.status_code == 200
    assert 'Dashboard' in response.content.decode()


@pytest.mark.django_db
def test_outbound_list_view():
    """Test outbound list view"""
    user = User.objects.create_user('testuser', 'test@example.com', 'testpass')
    client = Client()
    client.login(username='testuser', password='testpass')

    response = client.get('/outbound/')
    assert response.status_code == 200


def test_health_check():
    """Test health check endpoint"""
    client = Client()
    response = client.get('/healthz/')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
