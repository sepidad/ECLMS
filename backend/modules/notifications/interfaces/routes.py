"""Notifications and webhooks API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import current_user_id, require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.notifications.application.notification_service import (
  NotificationService,
)

router = APIRouter(tags=['notifications'])


class WebhookSubscribeRequest(BaseModel):
  url: str = Field(min_length=5, max_length=500)
  event_type: str = Field(min_length=1, max_length=100)
  secret: str = Field(min_length=6, max_length=100)


def _service(request: Request) -> NotificationService:
  return request.app.state.container.get_service('notifications.service')


@router.get('')
async def list_notifications(request: Request):
  try:
    actor_id = await current_user_id(request)
    actor = await require_permission(request, 'contract.read')
    service = _service(request)
    items = await service.list_notifications(actor_id, actor.organization_id)
    unread = await service.unread_count(actor_id, actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'items': [
        {
          'id': n.id,
          'subject': n.subject,
          'body': n.body,
          'channel': n.channel,
          'is_read': n.is_read,
          'created_at': n.created_at,
        }
        for n in items
      ],
      'unread_count': unread,
    },
    get_trace_id(),
  )


@router.post('/read-all')
async def mark_all_read(request: Request):
  try:
    actor_id = await current_user_id(request)
    actor = await require_permission(request, 'contract.read')
    marked = await _service(request).mark_all_read(actor_id, actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'marked': marked}, get_trace_id())


@router.post('/{notification_id}/read')
async def mark_read(notification_id: str, request: Request):
  try:
    actor = await require_permission(request, 'contract.read')
    await _service(request).mark_read(notification_id, actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'status': 'read'}, get_trace_id())


@router.post('/webhooks')
async def subscribe_webhook(payload: WebhookSubscribeRequest, request: Request):
  try:
    actor = await require_permission(request, 'user.manage')
    sub = await _service(request).subscribe_webhook(
      actor.organization_id, payload.url, payload.event_type, payload.secret,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'id': sub.id,
      'url': sub.url,
      'event_type': sub.event_type,
      'is_active': sub.is_active,
    },
    get_trace_id(),
  )


@router.get('/webhooks')
async def list_webhooks(request: Request):
  try:
    actor = await require_permission(request, 'user.manage')
    subs = await _service(request).list_subscriptions(actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(
    {
      'items': [
        {
          'id': s.id,
          'url': s.url,
          'event_type': s.event_type,
          'is_active': s.is_active,
        }
        for s in subs
      ]
    },
    get_trace_id(),
  )


@router.get('/webhooks/{webhook_id}/deliveries')
async def list_webhook_deliveries(webhook_id: str, request: Request, limit: int = 50, offset: int = 0):
  try:
    actor = await require_permission(request, 'user.manage')
    limit = max(1, min(limit, 200))
    offset = max(offset, 0)
    result = await _service(request).list_subscription_deliveries(
      actor.organization_id, webhook_id, limit=limit, offset=offset,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(result, get_trace_id())


@router.get('/email/deliveries')
async def list_email_deliveries(request: Request, limit: int = 50, offset: int = 0):
  try:
    actor = await require_permission(request, 'user.manage')
    limit = max(1, min(limit, 200))
    offset = max(offset, 0)
    result = await _service(request).list_email_deliveries(
      actor.organization_id, limit=limit, offset=offset,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(result, get_trace_id())


@router.get('/sms/deliveries')
async def list_sms_deliveries(request: Request, limit: int = 50, offset: int = 0):
  try:
    actor = await require_permission(request, 'user.manage')
    limit = max(1, min(limit, 200))
    offset = max(offset, 0)
    result = await _service(request).list_sms_deliveries(
      actor.organization_id, limit=limit, offset=offset,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(result, get_trace_id())
