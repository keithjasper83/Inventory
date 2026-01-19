import boto3
from botocore.exceptions import ClientError
from src.config import settings

class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME
        )
        self.bucket_media = settings.BUCKET_MEDIA
        self.bucket_docs = settings.BUCKET_DOCS

    def ensure_buckets(self):
        """Create buckets if they don't exist."""
        for bucket in [self.bucket_media, self.bucket_docs]:
            try:
                self.s3_client.head_bucket(Bucket=bucket)
            except ClientError:
                # Bucket does not exist, create it
                self.s3_client.create_bucket(Bucket=bucket)

    def upload_file(self, file_obj, key: str, content_type: str, bucket_type: str = "media"):
        """Upload a file-like object to S3."""
        bucket = self.bucket_media if bucket_type == "media" else self.bucket_docs
        self.s3_client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={'ContentType': content_type}
        )
        return key

    def get_presigned_url(self, key: str, bucket_type: str = "media", expiration=3600):
        """Generate a presigned URL for a file."""
        bucket = self.bucket_media if bucket_type == "media" else self.bucket_docs
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None

storage = StorageService()
