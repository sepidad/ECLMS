"""SQLAlchemy-backed finance repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from backend.core.exceptions import NotFoundError
from backend.modules.finances.domain.finance import (
  FinanceCommitment,
  FinancePayment,
)
from infrastructure.database.models.finances import (
  FinanceCommitmentModel,
  FinancePaymentModel,
)
from infrastructure.database.session import get_session_factory


def _to_domain_commitment(model: FinanceCommitmentModel) -> FinanceCommitment:
  commitment = FinanceCommitment(
    contract_id=model.contract_id,
    description=model.description,
    amount=model.amount,
    currency=model.currency,
    organization_id=model.organization_id,
    created_by=model.created_by,
    commitment_id=model.id,
  )
  commitment.status = model.status
  commitment.created_at = model.created_at
  commitment.updated_at = model.updated_at
  return commitment


def _to_domain_payment(model: FinancePaymentModel) -> FinancePayment:
  payment = FinancePayment(
    commitment_id=model.commitment_id,
    amount=model.amount,
    due_date=model.due_date,
    organization_id=model.organization_id,
    payment_id=model.id,
  )
  payment.status = model.status
  payment.paid_at = model.paid_at
  payment.created_at = model.created_at
  payment.updated_at = model.updated_at
  return payment


class SqlFinanceRepository:
  async def get_commitment_by_id(self, commitment_id: str) -> FinanceCommitment | None:
    async with get_session_factory()() as session:
      model = await session.get(FinanceCommitmentModel, commitment_id)
      return _to_domain_commitment(model) if model else None

  async def require_commitment(self, commitment_id: str) -> FinanceCommitment:
    commitment = await self.get_commitment_by_id(commitment_id)
    if commitment is None:
      raise NotFoundError(f'Commitment not found: {commitment_id}')
    return commitment

  async def get_payment_by_id(self, payment_id: str) -> FinancePayment | None:
    async with get_session_factory()() as session:
      model = await session.get(FinancePaymentModel, payment_id)
      if model is None:
        return None
      payment = FinancePayment(
        commitment_id=model.commitment_id,
        amount=model.amount,
        due_date=model.due_date,
        organization_id=model.organization_id,
        payment_id=model.id,
      )
      payment.status = model.status
      payment.paid_at = model.paid_at
      payment.created_at = model.created_at
      payment.updated_at = model.updated_at
      return payment

  async def require_payment(self, payment_id: str) -> FinancePayment:
    payment = await self.get_payment_by_id(payment_id)
    if payment is None:
      raise NotFoundError(f'Payment not found: {payment_id}')
    return payment

  async def save_commitment(self, commitment: FinanceCommitment) -> FinanceCommitment:
    async with get_session_factory()() as session:
      existing = await session.get(FinanceCommitmentModel, commitment.id)
      if existing is None:
        session.add(
          FinanceCommitmentModel(
            id=commitment.id,
            organization_id=commitment.organization_id,
            contract_id=commitment.contract_id,
            description=commitment.description,
            amount=commitment.amount,
            currency=commitment.currency,
            status=commitment.status,
            created_by=commitment.created_by,
            created_at=commitment.created_at,
            updated_at=commitment.updated_at,
          )
        )
      else:
        existing.description = commitment.description
        existing.amount = commitment.amount
        existing.currency = commitment.currency
        existing.status = commitment.status
        existing.updated_at = commitment.updated_at
      await session.commit()
    return commitment

  async def save_payment(self, payment: FinancePayment) -> FinancePayment:
    async with get_session_factory()() as session:
      existing = await session.get(FinancePaymentModel, payment.id)
      if existing is None:
        session.add(
          FinancePaymentModel(
            id=payment.id,
            organization_id=payment.organization_id,
            commitment_id=payment.commitment_id,
            amount=payment.amount,
            due_date=payment.due_date,
            status=payment.status,
            paid_at=payment.paid_at,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
          )
        )
      else:
        existing.amount = payment.amount
        existing.due_date = payment.due_date
        existing.status = payment.status
        existing.paid_at = payment.paid_at
        existing.updated_at = payment.updated_at
      await session.commit()
    return payment

  async def list_commitments_for_contract(
    self, contract_id: str, *, organization_id: str, limit: int = 100, offset: int = 0
  ) -> list[FinanceCommitment]:
    async with get_session_factory()() as session:
      stmt = (
        select(FinanceCommitmentModel)
        .where(
          FinanceCommitmentModel.contract_id == contract_id,
          FinanceCommitmentModel.organization_id == organization_id,
        )
        .order_by(FinanceCommitmentModel.created_at)
        .limit(limit)
        .offset(offset)
      )
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain_commitment(m) for m in models]

  async def list_all_commitments(
    self,
    *,
    organization_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[FinanceCommitment]:
    async with get_session_factory()() as session:
      stmt = select(FinanceCommitmentModel).where(
        FinanceCommitmentModel.organization_id == organization_id
      )
      if status is not None:
        stmt = stmt.where(FinanceCommitmentModel.status == status)
      stmt = stmt.order_by(FinanceCommitmentModel.created_at).limit(limit).offset(offset)
      models = (await session.execute(stmt)).scalars().all()
      return [_to_domain_commitment(m) for m in models]

  async def list_payments_for_commitment(
    self, commitment_id: str, *, organization_id: str
  ) -> list[FinancePayment]:
    async with get_session_factory()() as session:
      stmt = (
        select(FinancePaymentModel)
        .where(
          FinancePaymentModel.commitment_id == commitment_id,
          FinancePaymentModel.organization_id == organization_id,
        )
        .order_by(FinancePaymentModel.due_date)
      )
      models = (await session.execute(stmt)).scalars().all()
      payments = []
      for m in models:
        payment = FinancePayment(
          commitment_id=m.commitment_id,
          amount=m.amount,
          due_date=m.due_date,
          organization_id=m.organization_id,
          payment_id=m.id,
        )
        payment.status = m.status
        payment.paid_at = m.paid_at
        payment.created_at = m.created_at
        payment.updated_at = m.updated_at
        payments.append(payment)
      return payments

  async def list_all_payments(
    self,
    *,
    organization_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[FinancePayment]:
    async with get_session_factory()() as session:
      stmt = select(FinancePaymentModel).where(
        FinancePaymentModel.organization_id == organization_id
      )
      if status is not None:
        stmt = stmt.where(FinancePaymentModel.status == status)
      stmt = stmt.order_by(FinancePaymentModel.due_date).limit(limit).offset(offset)
      models = (await session.execute(stmt)).scalars().all()
      payments = []
      for m in models:
        payment = FinancePayment(
          commitment_id=m.commitment_id,
          amount=m.amount,
          due_date=m.due_date,
          organization_id=m.organization_id,
          payment_id=m.id,
        )
        payment.status = m.status
        payment.paid_at = m.paid_at
        payment.created_at = m.created_at
        payment.updated_at = m.updated_at
        payments.append(payment)
      return payments

  async def find_overdue_payments(self, *, as_of: datetime) -> list[FinancePayment]:
    async with get_session_factory()() as session:
      stmt = select(FinancePaymentModel).where(
        FinancePaymentModel.status == 'SCHEDULED',
        FinancePaymentModel.due_date < as_of,
      )
      models = (await session.execute(stmt)).scalars().all()
      payments = []
      for m in models:
        payment = FinancePayment(
          commitment_id=m.commitment_id,
          amount=m.amount,
          due_date=m.due_date,
          organization_id=m.organization_id,
          payment_id=m.id,
        )
        payment.status = m.status
        payment.paid_at = m.paid_at
        payment.created_at = m.created_at
        payment.updated_at = m.updated_at
        payments.append(payment)
      return payments