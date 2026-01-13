import uuid
from storages.backends.s3boto3 import S3Boto3Storage

class SupabaseS3Storage(S3Boto3Storage):
    def exists(self, name):
        return False

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                name_parts = name.rsplit(".", 1)
                if len(name_parts) == 2:
                    unique_name = f"{name_parts[0]}_{uuid.uuid4().hex[:8]}.{name_parts[1]}"
                else:
                    unique_name = f"{name}_{uuid.uuid4().hex[:8]}"
                return super()._save(unique_name, content)
            raise
