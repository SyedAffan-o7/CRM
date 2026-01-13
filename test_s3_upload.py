import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm_project.settings")
import django
django.setup()

from django.core.files.base import ContentFile
from crm_project.storage_backends import SupabaseS3Storage

def test_upload():
    storage = SupabaseS3Storage()

    # Create a small test file
    content = ContentFile(b"Hello Supabase S3!")
    file_name = "test_upload.txt"

    try:
        saved_name = storage.save(file_name, content)
        url = storage.url(saved_name)
        print("✅ Upload successful!")
        print("File saved as:", saved_name)
        print("Generated URL:", url)

        # Test if the URL is accessible
        import requests
        try:
            response = requests.head(url, timeout=10)
            print(f"URL accessibility: {response.status_code}")
            if response.status_code != 200:
                print("Response headers:", dict(response.headers))
        except Exception as e:
            print(f"URL access error: {e}")

    except Exception as e:
        print("❌ Upload failed:", str(e))

if __name__ == "__main__":
    test_upload()
