"""Tests for the ABAC policy engine (backend/api/abac.py)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.api.abac import (
  Actor,
  Policy,
  PolicyContext,
  PolicyEngine,
  action_is,
  all_of,
  any_of,
  is_resource_owner,
  is_same_organization,
  time_between,
)


@dataclass
class Contract:
  owner_id: str | None = None
  organization_id: str | None = None


def _actor(user: str = 'u1', org: str = 'org1') -> Actor:
  return Actor(id=user, organization_id=org)


def _ctx(actor, resource=None, action=None) -> PolicyContext:
  return PolicyContext(actor=actor, resource=resource, action=action)


def test_engine_no_policies_returns_true():
  engine = PolicyEngine()
  assert engine.evaluate(_ctx(_actor())) is True


def test_engine_explicit_allow():
  engine = PolicyEngine()
  engine.add_policy(Policy('owner', is_resource_owner, effect='allow'))
  contract = Contract(owner_id='u1')
  assert engine.evaluate(_ctx(_actor(), contract)) is True


def test_engine_deny_takes_precedence():
  engine = PolicyEngine()
  engine.add_policy(Policy('allow-owner', is_resource_owner, effect='allow'))
  engine.add_policy(Policy('deny-all', lambda ctx: True, effect='deny'))
  contract = Contract(owner_id='u1')
  assert engine.evaluate(_ctx(_actor(), contract)) is False


def test_is_resource_owner():
  assert is_resource_owner(_ctx(_actor(), Contract(owner_id='u1'))) is True
  assert is_resource_owner(_ctx(_actor(), Contract(owner_id='other'))) is False
  assert is_resource_owner(_ctx(_actor(), resource=None)) is False


def test_is_same_organization():
  assert is_same_organization(_ctx(_actor(), Contract(organization_id='org1'))) is True
  assert is_same_organization(_ctx(_actor(), Contract(organization_id='org2'))) is False
  assert is_same_organization(_ctx(_actor(), resource=None)) is False


def test_time_between():
  from datetime import UTC, datetime

  hour = datetime.now(UTC).hour
  assert time_between(hour, hour + 1)(_ctx(_actor())) is True
  assert time_between(-1, -1)(_ctx(_actor())) is False


def test_action_and_combinators():
  assert action_is('read')(_ctx(_actor(), action='read')) is True
  assert action_is('read', 'write')(_ctx(_actor(), action='read')) is True
  ctx = _ctx(_actor(), Contract(owner_id='u1'), action='read')
  assert all_of(is_resource_owner, action_is('read'))(ctx) is True
  assert any_of(is_resource_owner, action_is('delete'))(ctx) is True