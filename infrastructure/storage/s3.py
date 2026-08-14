"""AWS S3 / S3-compatible object storage provider.

Implements the StorageProvider contract on top of AWS S3 (or any
S3-compatible service such as MinIO / LocalStack) using boto3.
Blocking boto3 calls run in a thread pool via asyncio.to_thread so the
event loop is never blocked.
"""

from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import ClientError

from backend.config import get_settings
from backend.core.exceptions import StorageError
from infrastructure.storage.provider import StorageProvider


class S3StorageProvider(StorageProvider):
  """Stores document blobs in an S3 bucket."""

  def __init__(self) -> None:
    settings = get_settings()
    self._bucket = settings.s3_bucket
    self._client = boto3.client(
      's3',
      region_name=settings.s3_region,
      endpoint_url=settings.s3_endpoint_url,
      aws_access_key_id=settings.s3_access_key_id,
      aws_secret_access_key=settings.s3_secret_access_key,
    )

  async def put(self, key: str, content: bytes, *, content_type: str | None = None) -> None:
    def _put():
      kwargs = {'ContentType': content_type} if content_type else {}
      self._client.put_object(Bucket=self._bucket, Key=key, Body=content, **kwargs)

    try:
      await asyncio.to_thread(_put)
    except ClientError as exc:
      raise StorageError(f'Failed to upload blob to S3: {key}') from exc

  async def get(self, key: str) -> bytes:
    def _get():
      response = self._client.get_object(Bucket=self._bucket, Key=key)
      body = response['Body']
      return body.read() if hasattr(body, 'read') else body

    try:
      return await asyncio.to_thread(_get)
    except ClientError as exc:
      raise StorageError(f'Failed to read blob from S3: {key}') from exc

  async def delete(self, key: str) -> None:
    def _delete():
      self._client.delete_object(Bucket=self._bucket, Key=key)

    try:
      await asyncio.to_thread(_delete)
    except ClientError as exc:
      raise StorageError(f'Failed to delete blob from S3: {key}') from exc

  async def exists(self, key: str) -> bool:
    def _exists():
      try:
        self._client.head_object(Bucket=self._bucket, Key=key)
        return True
      except ClientError as exc:
        if exc.response['Error']['Code'] == '404':
          return False
        raise

    try:
      return await asyncio.to_thread(_exists)
    except ClientError as exc:
      raise StorageError(f'Failed to check blob in S3: {key}') from exc
