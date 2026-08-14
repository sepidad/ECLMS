"""Finance application service (Phase 2 contract financial tracking).

Coordinates financial commitments (contract value) and payment schedules.
Each mutation is org-scoped (ADR-003) and publishes domain events.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from backend.core.events import Event
from backend.core.exceptions import NotFoundError
from backend.core.utils import utc_now
from backend.modules.finances.domain.finance import (
  FinanceCommitment,
  FinancePayment,
)

if TYPE_CHECKING:
  from backend.core.events import EventBus
  from backend.modules.contracts.application.contract_service import ContractService
  from infrastructure.database.repositories.finance_repository import SqlFinanceRepository


class FinanceService:
  def __init__(
    self,
    repository: SqlFinanceRepository,
    contracts: ContractService,
    event_bus: EventBus,
  ) -> None:
    self._repository = repository
    self._contracts = contracts
    self._event_bus = event_bus

  async def _require_scoped_contract(self, contract_id: str, organization_id: str):
    return await self._contracts.get_contract(contract_id, organization_id=organization_id)

  async def create_commitment(
    self,
    *,
    contract_id: str,
    description: str,
    amount: float,
    currency: str,
    organization_id: str,
    created_by: str,
  ) -> FinanceCommitment:
    await self._require_scoped_contract(contract_id, organization_id)
    commitment = FinanceCommitment(
      contract_id=contract_id,
      description=description,
      amount=amount,
      currency=currency,
      organization_id=organization_id,
      created_by=created_by,
    )
    await self._repository.save_commitment(commitment)
    await self._event_bus.publish(
      Event(
        event_type='finance.commitment_created',
        source_module='finances',
        payload={
          'commitment_id': commitment.id,
          'contract_id': contract_id,
          'amount': amount,
          'currency': currency,
        },
        metadata={
          'entity_type': 'finance_commitment',
          'entity_id': commitment.id,
          'actor_id': created_by,
          'organization_id': organization_id,
        },
      )
    )
    return commitment

  async def create_payment(
    self,
    *,
    commitment_id: str,
    amount: float,
    due_date: datetime,
    organization_id: str,
  ) -> FinancePayment:
    commitment = await self._repository.require_commitment(commitment_id)
    if commitment.organization_id != organization_id:
      raise NotFoundError(f'Commitment not found: {commitment_id}')

    payment = FinancePayment(
      commitment_id=commitment_id,
      amount=amount,
      due_date=due_date,
      organization_id=organization_id,
    )
    await self._repository.save_payment(payment)
    await self._event_bus.publish(
      Event(
        event_type='finance.payment_scheduled',
        source_module='finances',
        payload={
          'payment_id': payment.id,
          'commitment_id': commitment_id,
          'amount': amount,
          'due_date': due_date.isoformat(),
        },
        metadata={
          'entity_type': 'finance_payment',
          'entity_id': payment.id,
          'actor_id': 'system',
          'organization_id': organization_id,
        },
      )
    )
    return payment

  async def mark_paid(
    self, payment_id: str, *, organization_id: str, actor_id: str
  ) -> FinancePayment:
    payment = await self._repository.require_payment(payment_id)
    if payment.organization_id != organization_id:
      raise NotFoundError(f'Payment not found: {payment_id}')

    payment.mark_paid()
    await self._repository.save_payment(payment)
    await self._event_bus.publish(
      Event(
        event_type='finance.payment_paid',
        source_module='finances',
        payload={
          'payment_id': payment.id,
          'commitment_id': payment.commitment_id,
          'amount': payment.amount,
        },
        metadata={
          'entity_type': 'finance_payment',
          'entity_id': payment.id,
          'actor_id': actor_id,
          'organization_id': organization_id,
        },
      )
    )
    return payment

  async def cancel_payment(
    self, payment_id: str, *, organization_id: str, actor_id: str
  ) -> FinancePayment:
    payment = await self._repository.require_payment(payment_id)
    if payment.organization_id != organization_id:
      raise NotFoundError(f'Payment not found: {payment_id}')

    payment.cancel()
    await self._repository.save_payment(payment)
    await self._event_bus.publish(
      Event(
        event_type='finance.payment_cancelled',
        source_module='finances',
        payload={'payment_id': payment.id, 'commitment_id': payment.commitment_id},
        metadata={
          'entity_type': 'finance_payment',
          'entity_id': payment.id,
          'actor_id': actor_id,
          'organization_id': organization_id,
        },
      )
    )
    return payment

  async def get_commitment(
    self, commitment_id: str, *, organization_id: str
  ) -> FinanceCommitment:
    commitment = await self._repository.require_commitment(commitment_id)
    if commitment.organization_id != organization_id:
      raise NotFoundError(f'Commitment not found: {commitment_id}')
    return commitment

  async def get_payment(
    self, payment_id: str, *, organization_id: str
  ) -> FinancePayment:
    payment = await self._repository.require_payment(payment_id)
    if payment.organization_id != organization_id:
      raise NotFoundError(f'Payment not found: {payment_id}')
    return payment

  async def list_commitments(
    self,
    contract_id: str,
    *,
    organization_id: str,
    limit: int = 100,
    offset: int = 0,
  ) -> list[FinanceCommitment]:
    await self._require_scoped_contract(contract_id, organization_id)
    return await self._repository.list_commitments_for_contract(
      contract_id, organization_id=organization_id, limit=limit, offset=offset
    )

  async def list_payments(
    self,
    commitment_id: str,
    *,
    organization_id: str,
    limit: int = 100,
    offset: int = 0,
  ) -> list[FinancePayment]:
    commitment = await self._repository.require_commitment(commitment_id)
    if commitment.organization_id != organization_id:
      raise NotFoundError(f'Commitment not found: {commitment_id}')
    return await self._repository.list_payments_for_commitment(
      commitment_id, organization_id=organization_id
    )

  async def list_all_commitments(
    self,
    *,
    organization_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[FinanceCommitment]:
    return await self._repository.list_all_commitments(
      organization_id=organization_id, status=status, limit=limit, offset=offset
    )

  async def list_all_payments(
    self,
    *,
    organization_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[FinancePayment]:
    return await self._repository.list_all_payments(
      organization_id=organization_id, status=status, limit=limit, offset=offset
    )

  async def sweep_overdue(self) -> int:
    now = utc_now()
    overdue = await self._repository.find_overdue_payments(as_of=now)
    count = 0
    for payment in overdue:
      if payment.mark_overdue():
        await self._repository.save_payment(payment)
        count += 1
        await self._event_bus.publish(
          Event(
            event_type='finance.payment_overdue',
            source_module='finances',
            payload={
              'payment_id': payment.id,
              'commitment_id': payment.commitment_id,
              'due_date': payment.due_date.isoformat(),
            },
            metadata={
              'entity_type': 'finance_payment',
              'entity_id': payment.id,
              'actor_id': 'system',
              'organization_id': payment.organization_id,
            },
          )
        )
    return count