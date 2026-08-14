"""Notifications & Integration application service & repository."""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import func, select, update

from backend.core.base.entity import Entity
from backend.core.events import Event
from backend.core.exceptions import NotFoundError
from infrastructure.database.models.integration import (
  EmailDeliveryModel,
  SmsDeliveryModel,
  WebhookDeliveryModel,
)
from infrastructure.database.models.notifications import (
  NotificationModel,
  WebhookSubscriptionModel,
)
from infrastructure.database.session import get_session_factory


class Notification(Entity):
  def __init__(
    self,
    recipient_id: str,
    organization_id: str,
    subject: str,
    body: str,
    channel: str = 'in_app',
    notification_id: str | None = None,
    is_read: bool = False,
    created_at=None,
  ) -> None:
    super().__init__(notification_id)
    self.recipient_id = recipient_id
    self.organization_id = organization_id
    self.subject = subject
    self.body = body
    self.channel = channel
    self.is_read = is_read
    if created_at is not None:
      self.created_at = created_at


class WebhookSubscription(Entity):
  def __init__(
    self,
    organization_id: str,
    url: str,
    event_type: str,
    secret: str,
    subscription_id: str | None = None,
  ) -> None:
    super().__init__(subscription_id)
    self.organization_id = organization_id
    self.url = url
    self.event_type = event_type
    self.secret = secret
    self.is_active = True


class NotificationRepository:
  async def create_notification(self, notification: Notification) -> Notification:
    async with get_session_factory()() as session:
      session.add(
        NotificationModel(
          id=notification.id,
          recipient_id=notification.recipient_id,
          organization_id=notification.organization_id,
          channel=notification.channel,
          subject=notification.subject,
          body=notification.body,
          is_read=notification.is_read,
          created_at=notification.created_at,
        )
      )
      await session.commit()
    return notification

  async def list_for_user(self, recipient_id: str, organization_id: str) -> list[Notification]:
    async with get_session_factory()() as session:
      stmt = (
        select(NotificationModel)
        .where(
          NotificationModel.recipient_id == recipient_id,
          NotificationModel.organization_id == organization_id,
        )
        .order_by(NotificationModel.created_at.desc())
      )
      models = (await session.execute(stmt)).scalars().all()
      return [
        Notification(
          recipient_id=m.recipient_id,
          organization_id=m.organization_id,
          subject=m.subject,
          body=m.body,
          channel=m.channel,
          notification_id=m.id,
          is_read=m.is_read,
          created_at=m.created_at,
        )
        for m in models
      ]

  async def count_unread(self, recipient_id: str, organization_id: str) -> int:
    async with get_session_factory()() as session:
      stmt = (
        select(func.count())
        .select_from(NotificationModel)
        .where(
          NotificationModel.recipient_id == recipient_id,
          NotificationModel.organization_id == organization_id,
          NotificationModel.is_read.is_(False),
        )
      )
      return int((await session.execute(stmt)).scalar_one())

  async def mark_read(self, notification_id: str, organization_id: str) -> None:
    async with get_session_factory()() as session:
      m = await session.get(NotificationModel, notification_id)
      if m is None or m.organization_id != organization_id:
        raise NotFoundError(f'Notification not found: {notification_id}')
      m.is_read = True
      await session.commit()

  async def mark_all_read(self, recipient_id: str, organization_id: str) -> int:
    async with get_session_factory()() as session:
      result = await session.execute(
        update(NotificationModel)
        .where(
          NotificationModel.recipient_id == recipient_id,
          NotificationModel.organization_id == organization_id,
          NotificationModel.is_read.is_(False),
        )
        .values(is_read=True)
      )
      await session.commit()
      return int(result.rowcount or 0)

  async def create_subscription(self, sub: WebhookSubscription) -> WebhookSubscription:
    async with get_session_factory()() as session:
      session.add(
        WebhookSubscriptionModel(
          id=sub.id,
          organization_id=sub.organization_id,
          url=sub.url,
          event_type=sub.event_type,
          secret=sub.secret,
          is_active=sub.is_active,
          created_at=sub.created_at,
        )
      )
      await session.commit()
    return sub

  async def list_subscriptions(self, organization_id: str) -> list[WebhookSubscription]:
    async with get_session_factory()() as session:
      stmt = select(WebhookSubscriptionModel).where(WebhookSubscriptionModel.organization_id == organization_id)
      models = (await session.execute(stmt)).scalars().all()
      return [
        WebhookSubscription(
          organization_id=m.organization_id,
          url=m.url,
          event_type=m.event_type,
          secret=m.secret,
          subscription_id=m.id,
        )
        for m in models
      ]

  async def list_active_for_event(self, organization_id: str, event_type: str) -> list[WebhookSubscription]:
    """Active subscriptions matching an event type (exact match or wildcard '*')."""
    async with get_session_factory()() as session:
      stmt = (
        select(WebhookSubscriptionModel)
        .where(
          WebhookSubscriptionModel.organization_id == organization_id,
          WebhookSubscriptionModel.is_active.is_(True),
          (WebhookSubscriptionModel.event_type == event_type) | (WebhookSubscriptionModel.event_type == '*'),
        )
      )
      models = (await session.execute(stmt)).scalars().all()
      return [
        WebhookSubscription(
          organization_id=m.organization_id,
          url=m.url,
          event_type=m.event_type,
          secret=m.secret,
          subscription_id=m.id,
        )
        for m in models
      ]

  async def list_deliveries(
    self,
    organization_id: str,
    subscription_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> list[dict]:
    """Recent webhook delivery attempts for a subscription (newest first)."""
    async with get_session_factory()() as session:
      stmt = (
        select(WebhookDeliveryModel)
        .where(
          WebhookDeliveryModel.organization_id == organization_id,
          WebhookDeliveryModel.subscription_id == subscription_id,
        )
        .order_by(WebhookDeliveryModel.delivered_at.desc())
        .limit(limit)
        .offset(offset)
      )
      rows = (await session.execute(stmt)).scalars().all()
      return [
        {
          'id': row.id,
          'event_type': row.event_type,
          'url': row.url,
          'status_code': row.status_code,
          'error': row.error,
          'delivered_at': row.delivered_at,
        }
        for row in rows
      ]

  async def delivery_summary(self, organization_id: str, subscription_id: str) -> dict:
    """Counts of successful vs failed deliveries for a subscription."""
    async with get_session_factory()() as session:
      total = 0
      failed = 0
      for row in (await session.execute(
        select(WebhookDeliveryModel).where(
          WebhookDeliveryModel.organization_id == organization_id,
          WebhookDeliveryModel.subscription_id == subscription_id,
        )
      )).scalars().all():
        total += 1
        if row.status_code is None or row.status_code >= 300:
          failed += 1
      return {'total': total, 'failed': failed, 'succeeded': total - failed}

  async def list_email_deliveries(
    self,
    organization_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> list[dict]:
    """Recent email delivery attempts for an organization (newest first)."""
    async with get_session_factory()() as session:
      stmt = (
        select(EmailDeliveryModel)
        .where(EmailDeliveryModel.organization_id == organization_id)
        .order_by(EmailDeliveryModel.delivered_at.desc())
        .limit(limit)
        .offset(offset)
      )
      rows = (await session.execute(stmt)).scalars().all()
      return [
        {
          'id': row.id,
          'recipient_id': row.recipient_id,
          'recipient_email': row.recipient_email,
          'event_type': row.event_type,
          'subject': row.subject,
          'body': row.body,
          'status': row.status,
          'error': row.error,
          'delivered_at': row.delivered_at,
        }
        for row in rows
      ]

  async def email_delivery_summary(self, organization_id: str) -> dict:
    """Counts of sent vs failed email deliveries for an organization."""
    async with get_session_factory()() as session:
      total = 0
      failed = 0
      for row in (await session.execute(
        select(EmailDeliveryModel).where(EmailDeliveryModel.organization_id == organization_id)
      )).scalars().all():
        total += 1
        if row.status != 'sent':
          failed += 1
      return {'total': total, 'failed': failed, 'sent': total - failed}

  async def list_sms_deliveries(
    self,
    organization_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> list[dict]:
    """Recent SMS delivery attempts for an organization (newest first)."""
    async with get_session_factory()() as session:
      stmt = (
        select(SmsDeliveryModel)
        .where(SmsDeliveryModel.organization_id == organization_id)
        .order_by(SmsDeliveryModel.delivered_at.desc())
        .limit(limit)
        .offset(offset)
      )
      rows = (await session.execute(stmt)).scalars().all()
      return [
        {
          'id': row.id,
          'recipient_id': row.recipient_id,
          'recipient_phone': row.recipient_phone,
          'event_type': row.event_type,
          'body': row.body,
          'status': row.status,
          'error': row.error,
          'delivered_at': row.delivered_at,
        }
        for row in rows
      ]

  async def sms_delivery_summary(self, organization_id: str) -> dict:
    """Counts of sent vs failed SMS deliveries for an organization."""
    async with get_session_factory()() as session:
      total = 0
      failed = 0
      for row in (await session.execute(
        select(SmsDeliveryModel).where(SmsDeliveryModel.organization_id == organization_id)
      )).scalars().all():
        total += 1
        if row.status != 'sent':
          failed += 1
      return {'total': total, 'failed': failed, 'sent': total - failed}


class NotificationService:
  def __init__(
    self,
    repository: NotificationRepository,
    user_repository=None,
  ) -> None:
    self._repository = repository
    self._users = user_repository

  #: Route domain events to in-app notification templates.
  #: Each mapping lists the audience roles (org scoped).  ``None`` means
  #: "no in-app notification" for that event type.
  ROUTES: ClassVar[dict[str, tuple[str, str, tuple[str, ...]]]] = {
    'workflow.started': (
      'Workflow Started',
      'Workflow {workflow_id} started for contract {contract_id} (step: {current_step}).',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'workflow.step_decided': (
      'Workflow Decision Recorded',
      'Step {step} was {decision} on workflow {workflow_id}.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'workflow.paused': (
      'Workflow Paused',
      'Workflow {workflow_id} for contract {contract_id} was paused.',
      ('ADMIN',),
    ),
    'workflow.resumed': (
      'Workflow Resumed',
      'Workflow {workflow_id} for contract {contract_id} resumed.',
      ('ADMIN',),
    ),
    'workflow.step_delegated': (
      'Workflow Step Delegated',
      'Step {step} on workflow {workflow_id} delegated.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'workflow.step_escalated': (
      'Workflow Step Escalated',
      'Step {step} on workflow {workflow_id} escalated to {escalation_role}.',
      ('ADMIN',),
    ),
    'contract.created': (
      'Contract Created',
      'Contract {contract_id} created.',
      ('CONTRACT_MANAGER',),
    ),
    'contract.state_changed': (
      'Contract State Changed',
      'Contract {contract_id} transitioned {from} -> {to}.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'document.uploaded': (
      'Document Uploaded',
      'Document uploaded for contract {contract_id}.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'obligation.created': (
      'Obligation Created',
      'Obligation {obligation_id} created for contract {contract_id} (due {due_date}).',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'obligation.completed': (
      'Obligation Completed',
      'Obligation {obligation_id} for contract {contract_id} completed.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'obligation.overdue': (
      'Obligation Overdue',
      'Obligation {obligation_id} (contract {contract_id}) is now OVERDUE.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
    'finance.payment_overdue': (
      'Payment Overdue',
      'Payment for contract {contract_id} is OVERDUE.',
      ('ADMIN', 'CONTRACT_MANAGER'),
    ),
  }

  async def notify(self, recipient_id: str, organization_id: str, subject: str, body: str, channel: str = 'in_app') -> Notification:
    notif = Notification(recipient_id, organization_id, subject, body, channel)
    return await self._repository.create_notification(notif)

  async def list_notifications(self, recipient_id: str, organization_id: str) -> list[Notification]:
    return await self._repository.list_for_user(recipient_id, organization_id)

  async def unread_count(self, recipient_id: str, organization_id: str) -> int:
    return await self._repository.count_unread(recipient_id, organization_id)

  async def mark_read(self, notification_id: str, organization_id: str) -> None:
    await self._repository.mark_read(notification_id, organization_id)

  async def mark_all_read(self, recipient_id: str, organization_id: str) -> int:
    return await self._repository.mark_all_read(recipient_id, organization_id)

  async def subscribe_webhook(self, organization_id: str, url: str, event_type: str, secret: str) -> WebhookSubscription:
    sub = WebhookSubscription(organization_id, url, event_type, secret)
    return await self._repository.create_subscription(sub)

  async def list_subscriptions(self, organization_id: str) -> list[WebhookSubscription]:
    return await self._repository.list_subscriptions(organization_id)

  async def list_subscription_deliveries(
    self,
    organization_id: str,
    subscription_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> dict:
    sub = await self._require_subscription(organization_id, subscription_id)
    items = await self._repository.list_deliveries(
      organization_id, sub.id, limit=limit, offset=offset
    )
    summary = await self._repository.delivery_summary(organization_id, sub.id)
    return {'items': items, 'subscription_id': sub.id, **summary}

  async def list_email_deliveries(
    self,
    organization_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> dict:
    items = await self._repository.list_email_deliveries(
      organization_id, limit=limit, offset=offset
    )
    summary = await self._repository.email_delivery_summary(organization_id)
    return {'items': items, **summary}

  async def list_sms_deliveries(
    self,
    organization_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
  ) -> dict:
    items = await self._repository.list_sms_deliveries(
      organization_id, limit=limit, offset=offset
    )
    summary = await self._repository.sms_delivery_summary(organization_id)
    return {'items': items, **summary}

  async def _require_subscription(self, organization_id: str, subscription_id: str) -> WebhookSubscription:
    for sub in await self._repository.list_subscriptions(organization_id):
      if sub.id == subscription_id:
        return sub
    raise NotFoundError(f'Webhook subscription not found: {subscription_id}')

  async def _recipients_for(self, organization_id: str, roles: tuple[str, ...]) -> set[str]:
    """Resolve in-organization user ids that hold at least one of the roles."""
    ids: set[str] = set()
    if self._users is None:
      return ids
    for role in roles:
      for user in await self._users.list_by_role_in_org(organization_id, role):
        ids.add(user.id)
    return ids

  async def handle_event(self, event: Event) -> None:
    """Create in-app notifications when domain events fire.

    Audiences are derived from the event type routing table and resolved
    to in-organization users by role.  Unrouted events are skipped.
    """
    route = self.ROUTES.get(event.event_type)
    if route is None:
      return
    subject_template, body_template, roles = route
    organization_id = event.metadata.get('organization_id')
    if not organization_id:
      return
    recipient_ids = await self._recipients_for(organization_id, roles)
    actor_id = event.metadata.get('actor_id')
    if actor_id and actor_id != 'system':
      recipient_ids.add(actor_id)
    if not recipient_ids:
      return
    payload = {**event.payload}
    try:
      subject = subject_template.format(**payload)
      body = body_template.format(**payload)
    except (KeyError, ValueError):
      subject, body = subject_template, f'{event.event_type}: {event.payload}'
    for recipient_id in recipient_ids:
      await self.notify(recipient_id, organization_id, subject, body)
