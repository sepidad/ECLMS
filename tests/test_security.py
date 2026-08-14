"""Unit tests for password hashing and JWT helpers."""

import pytest


def test_hash_and_verify_password():
  from backend.modules.identity.application.auth_service import hash_password, verify_password

  password_hash = hash_password('s3cret!')
  assert password_hash != 's3cret!'
  assert verify_password('s3cret!', password_hash)
  assert not verify_password('wrong', password_hash)


def test_verify_rejects_invalid_hash():
  from backend.modules.identity.application.auth_service import verify_password

  assert not verify_password('anything', 'not-a-bcrypt-hash')


def test_jwt_roundtrip():
  from backend.core.security import create_jwt, decode_jwt

  payload = {'sub': 'user-1', 'org': 'org-default'}
  secret = 'a-secret-key-that-is-at-least-32-bytes-long!!'
  token = create_jwt(payload, secret)
  decoded = decode_jwt(token, secret)
  assert decoded['sub'] == 'user-1'
  assert decoded['org'] == 'org-default'


def test_jwt_rejects_bad_signature():
  import jwt

  from backend.core.security import create_jwt, decode_jwt

  token = create_jwt({'sub': 'user-1'}, 'a-secret-key-that-is-at-least-32-bytes-long!!')
  with pytest.raises(jwt.InvalidSignatureError):
    decode_jwt(token, 'a-different-secret-key-that-is-also-32-bytes!!')
