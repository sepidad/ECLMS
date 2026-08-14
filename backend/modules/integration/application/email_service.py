"""SMTP Email delivery integration service.

Subscribes to the internal event bus and sends email notifications to the
same role-based audiences as in-app notifications.  Each send attempt is
recorded in ``email_deliveries`` for auditability and delivery history
(mirroring ``WebhookDeliveryService``).
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from backend.core.events import Event
from backend.core.logging import get_logger
from backend.core.utils import new_id, utc_now
from backend.modules.notifications.application.notification_service import NotificationService
from infrastructure.database.models.integration import EmailDeliveryModel
from infrastructure.database.session import get_session_factory

logger = get_logger('eclms.integration.email')

#: Subject/body templates + audience roles, shared with in-app notifications.
EMAIL_ROUTES = NotificationService.ROUTES


class EmailDeliveryService:
  """Delivers notifications and domain alerts via SMTP.

  Args:
    settings: Application settings (SMTP + email enabled flags).
    user_repository: Optional user store used to resolve role audiences
        by email address.  When omitted, no recipients can be resolved
        and events are skipped.
    repository: Optional notification repository used to persist
        ``EmailDeliveryModel`` records.  When omitted, deliveries are
        sent but not recorded.
  """

  def __init__(self, settings, user_repository=None, repository=None) -> None:
    self._settings = settings
    self._users = user_repository
    self._repository = repository

  async def handle_event(self, event: Event) -> None:
    """Handle domain events that warrant email notification.

    Audience resolution mirrors the in-app notification router: users in
    the org holding the routed roles, plus the actor who triggered the
    event.  Each recipient email is sent and the attempt recorded.
    """
    if not self._settings.email_enabled:
      return

    route = EMAIL_ROUTES.get(event.event_type)
    if route is None:
      return
    subject_template, body_template, roles = route

    organization_id = event.metadata.get('organization_id')
    if not organization_id:
      return

    recipients = await self._recipients_for(organization_id, roles, event)
    if not recipients:
      return

    payload = {**event.payload}
    try:
      subject = f'[ECLMS] {subject_template.format(**payload)}'
      body = body_template.format(**payload)
    except (KeyError, ValueError):
      subject = f'[ECLMS] {subject_template}'
      body = f'{event.event_type}: {event.payload}'

    for user in recipients:
      if not user.email:
        continue
      await self.send_email(
        to=user.email,
        subject=subject,
        body=body,
        organization_id=organization_id,
        recipient_id=user.id,
        event_type=event.event_type,
      )

  async def _recipients_for(self, organization_id: str, roles: tuple[str, ...], event: Event) -> list:
    """Resolve in-organization users (with email addresses) for the roles + actor."""
    users: dict[str, object] = {}
    if self._users is not None:
      for role in roles:
        for user in await self._users.list_by_role_in_org(organization_id, role):
          users[user.id] = user
    actor_id = event.metadata.get('actor_id')
    if actor_id and actor_id != 'system' and self._users is not None:
      actor = await self._users.get_by_id(actor_id)
      if actor is not None and actor.organization_id == organization_id:
        users[actor.id] = actor
    return list(users.values())

  async def send_email(
    self,
    *,
    to: str,
    subject: str,
    body: str,
    organization_id: str | None = None,
    recipient_id: str | None = None,
    event_type: str | None = None,
  ) -> dict:
    """Send an email via SMTP (run blocking smtplib in thread pool).

    Records the attempt in ``email_deliveries`` when an organization is
    provided.  Returns ``{'success': bool, 'error': str | None}``.
    """
    success = True
    error: str | None = None
    try:
      await asyncio.to_thread(self._send, to, subject, body)
    except Exception as exc:
      success = False
      error = str(exc)
      logger.exception('Failed to send email to %s', to)

    if organization_id:
      await self._record(
        organization_id=organization_id,
        recipient_id=recipient_id or 'system',
        recipient_email=to,
        event_type=event_type or 'manual',
        subject=subject,
        body=body,
        success=success,
        error=error,
      )
    return {'success': success, 'error': error}

  def _send(self, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = self._settings.smtp_from
    msg['To'] = to

    if self._settings.smtp_host == 'localhost' and not self._settings.smtp_user:
      logger.info('Mock SMTP email sent to %s: %s', to, subject)
      return

    with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
      if self._settings.smtp_user:
        server.starttls()
        server.login(self._settings.smtp_user, self._settings.smtp_password)
      server.send_message(msg)
      logger.info('SMTP email successfully delivered to %s', to)

  async def _record(
    self,
    *,
    organization_id: str,
    recipient_id: str,
    recipient_email: str,
    event_type: str,
    subject: str,
    body: str,
    success: bool,
    error: str | None,
  ) -> str:
    delivery_id = new_id()
    async with get_session_factory()() as session:
      session.add(
        EmailDeliveryModel(
          id=delivery_id,
          organization_id=organization_id,
          recipient_id=recipient_id,
          recipient_email=recipient_email,
          event_type=event_type,
          subject=subject,
          body=body,
          status='sent' if success else 'failed',
          error=error,
          delivered_at=utc_now(),
        )
      )
      await session.commit()
    return delivery_id
