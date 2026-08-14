"""Runtime configuration (deployment/09_Runtime_Configuration.md).

Configuration is hierarchical and environment-driven.  Sensitive values
(secrets) must never be defined here; they come from environment
variables, secret stores, or deployment profiles.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Marker value in .env.example.  Production/staging must supply a real secret.
DEV_SECRET_MARKER = 'dev-only-insecure-secret-key-please-rotate-0123456789'
PROD_ENVIRONMENTS = ('production', 'staging')


class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_prefix='ECLMS_',
    env_file='.env',
    env_file_encoding='utf-8',
    extra='ignore',
    case_sensitive=False,
  )

  app_name: str = 'ECLMS'
  app_version: str = '0.1.0'
  environment: str = 'development'

  # Logging
  log_level: str = 'INFO'
  json_logs: bool = True

  # Security
  jwt_secret: str = Field(default=DEV_SECRET_MARKER, repr=False)
  jwt_algorithm: str = 'HS256'
  jwt_expire_minutes: int = 60

  # Database
  database_url: str = 'postgresql+asyncpg://eclms:eclms@localhost:5432/eclms'
  database_echo: bool = False
  database_pool_size: int = 10
  database_max_overflow: int = 20
  #: Verify pooled connections are alive before checkout (resilience to
  #: dropped connections / DB restarts behind a proxy).
  database_pool_pre_ping: bool = True
  #: Recycled pooled connections after N seconds to avoid stale sockets
  #: from idle connections killed by the server or a firewall.
  database_pool_recycle: int = 3600

  # Storage
  storage_root: str = './var/storage'
  storage_backend: str = 'local'  # 'local' or 's3'
  s3_bucket: str = 'eclms-documents'
  s3_region: str = 'us-east-1'
  s3_endpoint_url: str | None = None
  s3_access_key_id: str | None = None
  s3_secret_access_key: str | None = Field(default=None, repr=False)

  # Scheduler / background jobs
  scheduler_enabled: bool = False
  escalation_interval_minutes: int = 30

  # Event transport ('memory' for in-process, 'redis' for durable)
  event_transport: str = 'memory'
  redis_url: str = 'redis://localhost:6379/0'
  redis_event_stream: str = 'eclms:events'
  redis_consumer_group: str = 'eclms:messages'

  # API
  api_v1_prefix: str = '/api/v1'
  cors_origins: list[str] = Field(default_factory=lambda: ['*'])
  # Honor X-Forwarded-* headers when behind a reverse proxy (TLS).
  trusted_proxy: bool = False

  # API hardening (rate limiting + request body size)
  #: Enable in-process fixed-window rate limiting (default 100 req / 60s per client).
  rate_limit_enabled: bool = False
  rate_limit_requests: int = 100
  rate_limit_window_seconds: int = 60
  #: Maximum request body size in bytes (0 = unlimited). Applied to the
  #: Content-Length header in a shared middleware.
  max_request_bytes: int = 0

  # Email / SMTP integration
  email_enabled: bool = False
  smtp_host: str = 'localhost'
  smtp_port: int = 587
  smtp_user: str = ''
  smtp_password: str = Field(default='', repr=False)
  smtp_from: str = 'eclms@eclms.local'

  # SMS integration (provider 'mock' logs; other providers plug in via the abstraction)
  sms_enabled: bool = False
  sms_provider: str = 'mock'  # 'mock' | 'http'
  #: Comma-separated default recipient phone numbers (E.164) used when an
  #: event carries no explicit recipient.
  sms_recipients: str = ''
  #: HTTP SMS gateway URL/username for the 'http' provider (optional).
  sms_http_url: str = ''
  sms_http_username: str = ''
  sms_http_password: str = Field(default='', repr=False)

  # External system connectors (ERP / accounting).  When the endpoint is
  # empty a dry-run sync returns a result without sending anything.
  erp_endpoint: str = ''
  accounting_endpoint: str = ''

  # OIDC / External Identity Provider
  oidc_enabled: bool = False
  oidc_issuer: str = ''
  oidc_client_id: str = ''
  oidc_client_secret: str = Field(default='', repr=False)
  oidc_scopes: list[str] = Field(default_factory=lambda: ['openid', 'email', 'profile'])
  oidc_redirect_uri: str = ''
  oidc_default_org: str = 'org-default'
  #: Server-to-server base URL used for the token/userinfo endpoints.  When
  #: empty, falls back to ``oidc_issuer``.  In Docker compose the browser
  #: needs ``http://localhost:8080/realms/eclms`` while the API container must
  #: reach Keycloak via the internal name (``http://keycloak:8080/realms/eclms``).
  oidc_internal_issuer: str = ''

  # AI-assisted contract review
  #: 'rules' uses the deterministic in-process analyzer; 'llm' calls an
  #: OpenAI-compatible chat completions endpoint.
  ai_review_provider: str = 'rules'
  llm_api_url: str = ''
  llm_api_key: str = Field(default='', repr=False)
  llm_model: str = 'gpt-4o-mini'
  llm_timeout_seconds: int = 30

  @model_validator(mode='after')
  def _validate_secrets_for_environment(self) -> Settings:
    if self.environment.lower() in PROD_ENVIRONMENTS:
      if not self.jwt_secret or self.jwt_secret == DEV_SECRET_MARKER:
        raise ValueError('ECLMS_JWT_SECRET must be set to a strong secret in production/staging')
      if len(self.jwt_secret) < 32:
        raise ValueError('ECLMS_JWT_SECRET must be at least 32 characters in production/staging')
    return self


@lru_cache
def get_settings() -> Settings:
  return Settings()
