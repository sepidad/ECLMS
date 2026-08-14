"""Tests for the S3 storage provider using botocore Stubber (no network)."""

from __future__ import annotations

import pytest
from botocore.stub import Stubber

from backend.core.exceptions import StorageError
from infrastructure.storage import get_storage_provider
from infrastructure.storage.s3 import S3StorageProvider


@pytest.mark.anyio
async def test_s3_storage_provider_roundtrip():
  provider = S3StorageProvider()
  with Stubber(provider._client) as stubber:
    stubber.add_response('put_object', {}, {'Bucket': provider._bucket, 'Key': 'contracts/abc.pdf', 'Body': b'data', 'ContentType': 'application/pdf'})
    stubber.add_response('head_object', {'ResponseMetadata': {}}, {'Bucket': provider._bucket, 'Key': 'contracts/abc.pdf'})
    stubber.add_response('get_object', {'Body': b'data'}, {'Bucket': provider._bucket, 'Key': 'contracts/abc.pdf'})
    stubber.add_response('delete_object', {}, {'Bucket': provider._bucket, 'Key': 'contracts/abc.pdf'})

    await provider.put('contracts/abc.pdf', b'data', content_type='application/pdf')
    assert await provider.exists('contracts/abc.pdf') is True
    assert await provider.get('contracts/abc.pdf') == b'data'
    await provider.delete('contracts/abc.pdf')
    stubber.assert_no_pending_responses()


@pytest.mark.anyio
async def test_s3_storage_provider_missing_raises_storage_error():
  provider = S3StorageProvider()
  with Stubber(provider._client) as stubber:
    stubber.add_client_error('get_object', service_error_code='NoSuchKey')

    with pytest.raises(StorageError):
      await provider.get('contracts/missing.pdf')


def test_storage_factory_returns_configured_backend():
  from backend.config import get_settings

  get_settings.cache_clear()
  provider = get_storage_provider()
  assert provider is not None
  get_settings.cache_clear()
