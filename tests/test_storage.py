import io
import boto3
import pytest
from moto import mock_aws
from botocore.exceptions import ClientError
from unittest.mock import patch
from src.config import settings
from src.storage import StorageService

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture
def mock_s3(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")

@pytest.fixture
def storage_service(mock_s3):
    # Initialize the StorageService with the mocked S3 client
    # Note: we need to recreate the client inside the mock context
    # to ensure it intercepts boto3 calls.
    service = StorageService()
    # Replace the client with our mock_s3 client that doesn't have custom endpoint_url
    # which might bypass moto if set to something else in settings.
    service.s3_client = mock_s3
    service.bucket_media = "test-media-bucket"
    service.bucket_docs = "test-docs-bucket"
    return service

def test_ensure_buckets(storage_service, mock_s3):
    # Act
    storage_service.ensure_buckets()

    # Assert buckets exist
    response = mock_s3.list_buckets()
    buckets = [bucket['Name'] for bucket in response['Buckets']]
    assert storage_service.bucket_media in buckets
    assert storage_service.bucket_docs in buckets

    # Act again - should handle existing buckets gracefully
    storage_service.ensure_buckets()

def test_upload_file(storage_service, mock_s3):
    # Arrange
    storage_service.ensure_buckets()
    file_content = b"test file content"
    # Need separate BytesIO instances for each upload because upload_fileobj
    # reads from the file-like object and might close it or we just need fresh objects.
    # Actually seek(0) should be fine, but the error said "I/O operation on closed file"
    # which means upload_fileobj closed it.

    file_obj = io.BytesIO(file_content)
    key = "test-folder/test-file.txt"
    content_type = "text/plain"

    # Act for media bucket
    returned_key = storage_service.upload_file(file_obj, key, content_type, bucket_type="media")

    # Assert
    assert returned_key == key
    response = mock_s3.get_object(Bucket=storage_service.bucket_media, Key=key)
    assert response['Body'].read() == file_content
    assert response['ContentType'] == content_type

    # Act for docs bucket
    file_obj2 = io.BytesIO(file_content)
    returned_key_docs = storage_service.upload_file(file_obj2, key, content_type, bucket_type="docs")
    assert returned_key_docs == key
    response_docs = mock_s3.get_object(Bucket=storage_service.bucket_docs, Key=key)
    assert response_docs['Body'].read() == file_content

@patch("src.storage.settings_manager.get", return_value=3600)
def test_get_presigned_url(mock_get, storage_service, mock_s3):
    # Arrange
    storage_service.ensure_buckets()
    file_content = b"test"
    key = "test.txt"
    mock_s3.put_object(Bucket=storage_service.bucket_media, Key=key, Body=file_content)

    # Act
    url = storage_service.get_presigned_url(key, bucket_type="media")

    # Assert
    assert url is not None
    assert isinstance(url, str)
    assert storage_service.bucket_media in url
    assert key in url
    assert "AWSAccessKeyId" in url or "X-Amz-Credential" in url

@patch("src.storage.settings_manager.get", return_value=3600)
def test_get_presigned_url_client_error(mock_get, storage_service, mock_s3):
    # Arrange
    # Force a ClientError by patching generate_presigned_url
    with patch.object(storage_service.s3_client, 'generate_presigned_url', side_effect=ClientError({'Error': {'Code': '500', 'Message': 'Error'}}, 'operation_name')):
        # Act
        url = storage_service.get_presigned_url("nonexistent.txt")

        # Assert
        assert url is None
