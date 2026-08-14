"""ABAC (Attribute-Based Access Control) policy engine.

Extends the existing RBAC with attribute-based policies that can evaluate
user attributes, resource attributes, and environment context for fine-grained
authorization decisions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Actor:
  """The authenticated principal plus their tenant."""

  id: str
  organization_id: str


@dataclass(frozen=True)
class PolicyContext:
  """Context available to policy evaluation."""

  actor: Actor
  resource: Any | None = None
  action: str | None = None
  environment: dict[str, Any] | None = None


class Policy:
  """A single ABAC policy rule.

  Policies are expressed as callable predicates that receive a PolicyContext
  and return True (allow) or False (deny).
  """

  def __init__(
    self,
    name: str,
    predicate: Callable[[PolicyContext], bool],
    description: str = '',
    effect: str = 'allow',
  ) -> None:
    self.name = name
    self._predicate = predicate
    self.description = description
    self.effect = effect  # 'allow' or 'deny'

  def evaluate(self, ctx: PolicyContext) -> bool:
    try:
      return bool(self._predicate(ctx))
    except Exception:  # noqa: BLE001 - policy failure must never crash authorization
      return False


class PolicyEngine:
  """Evaluates a set of policies for a given context.

  Policies are evaluated in order; DENY effects take precedence over ALLOW.
  If no policy matches, the default is DENY (implicit deny).
  """

  def __init__(self) -> None:
    self._policies: list[Policy] = []

  def add_policy(self, policy: Policy) -> None:
    self._policies.append(policy)

  def clear(self) -> None:
    self._policies.clear()

  def evaluate(self, ctx: PolicyContext) -> bool:
    """Return True if access is granted, False otherwise."""
    if not self._policies:
      return True  # no ABAC policies registered → fall through to RBAC only

    has_allow = False
    for policy in self._policies:
      if policy.evaluate(ctx):
        if policy.effect == 'deny':
          return False
        has_allow = True
    return has_allow


def is_resource_owner(ctx: PolicyContext) -> bool:
  """Allow if actor.id matches resource.owner_id or resource.created_by."""
  if ctx.resource is None:
    return False
  owner = getattr(ctx.resource, 'owner_id', None) or getattr(ctx.resource, 'created_by', None)
  return owner == ctx.actor.id


def is_same_organization(ctx: PolicyContext) -> bool:
  """Allow if actor and resource share the same organization_id."""
  if ctx.resource is None:
    return False
  return getattr(ctx.resource, 'organization_id', None) == ctx.actor.organization_id


def time_between(start_hour: int, end_hour: int):
  """Allow only between start_hour and end_hour (UTC)."""
  from datetime import UTC, datetime

  def _check(ctx: PolicyContext) -> bool:
    now = datetime.now(UTC).hour
    return start_hour <= now < end_hour

  return _check


def action_is(*actions: str):
  """Allow only for specific actions."""

  def _check(ctx: PolicyContext) -> bool:
    return ctx.action in actions

  return _check


def all_of(*predicates):
  return lambda ctx: all(p(ctx) for p in predicates)


def any_of(*predicates):
  return lambda ctx: any(p(ctx) for p in predicates)
