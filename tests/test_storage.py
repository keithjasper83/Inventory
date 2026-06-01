import io
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.storage import StorageService


@pytest.fixture
def storage_service():
    service = StorageService.__new__(StorageService)
    service.s3_client = MagicMock()
    service.bucket_media = "test-media-bucket"
    service.bucket_docs = "test-docs-bucket"
    return service


def test_ensure_buckets(storage_service):
    storage_service.s3_client.head_bucket.side_effect = [
        ClientError({"Error": {"Code": "404"}}, "HeadBucket"),
        None,
    ]

    storage_service.ensure_buckets()

    storage_service.s3_client.head_bucket.assert_any_call(Bucket=storage_service.bucket_media)
    storage_service.s3_client.head_bucket.assert_any_call(Bucket=storage_service.bucket_docs)
    storage_service.s3_client.create_bucket.assert_called_once_with(Bucket=storage_service.bucket_media)


def test_upload_file(storage_service):
    file_obj = io.BytesIO(b"test file content")
    key = "test-folder/test-file.txt"
    content_type = "text/plain"

    returned_key = storage_service.upload_file(file_obj, key, content_type, bucket_type="media")

    assert returned_key == key
    storage_service.s3_client.upload_fileobj.assert_called_once_with(
        file_obj,
        storage_service.bucket_media,
        key,
        ExtraArgs={"ContentType": content_type},
    )

    storage_service.s3_client.upload_fileobj.reset_mock()

    file_obj2 = io.BytesIO(b"test file content")
    returned_key_docs = storage_service.upload_file(file_obj2, key, content_type, bucket_type="docs")

    assert returned_key_docs == key
    storage_service.s3_client.upload_fileobj.assert_called_once_with(
        file_obj2,
        storage_service.bucket_docs,
        key,
        ExtraArgs={"ContentType": content_type},
    )


@patch("src.storage.settings_manager.get", return_value=3600)
def test_get_presigned_url(mock_get, storage_service):
    key = "test.txt"
    storage_service.s3_client.generate_presigned_url.return_value = "https://example.com/test.txt"

    url = storage_service.get_presigned_url(key, bucket_type="media")

    assert url == "https://example.com/test.txt"
    storage_service.s3_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": storage_service.bucket_media, "Key": key},
        ExpiresIn=3600,
    )


@patch("src.storage.settings_manager.get", return_value=3600)
def test_get_presigned_url_client_error(mock_get, storage_service):
    with patch.object(
        storage_service.s3_client,
        "generate_presigned_url",
        side_effect=ClientError({"Error": {"Code": "500", "Message": "Error"}}, "operation_name"),
    ):
        url = storage_service.get_presigned_url("nonexistent.txt")

    assert url is None
