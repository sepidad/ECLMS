"""SQLAlchemy ORM models for the workflow module.

Implements the workflow data model from DATA-019 section 5.4:
- WorkflowInstance (a running approval execution for a contract)
- WorkflowStep (a single approval step within an instance)
- WorkflowHistory (immutable transition log for the instance)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.session import Base


class WorkflowInstanceModel(Base):
  __tablename__ = 'workflow_instances'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  contract_id: Mapped[str] = mapped_column(
    String(32), ForeignKey('contracts.id', name='fk_workflow_instances_contract'), index=True, nullable=False
  )
  definition_id: Mapped[str] = mapped_column(String(100), nullable=False)
  status: Mapped[str] = mapped_column(String(30), nullable=False, default='RUNNING', index=True)
  current_step_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
  started_by: Mapped[str] = mapped_column(String(32), nullable=False)
  # Phase 2: pause state
  paused_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
  pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
  paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

  steps: Mapped[list[WorkflowStepModel]] = relationship(
    back_populates='instance', lazy='selectin', order_by='WorkflowStepModel.step_number'
  )
  history: Mapped[list[WorkflowHistoryModel]] = relationship(
    back_populates='instance', lazy='selectin', order_by='WorkflowHistoryModel.created_at'
  )


class WorkflowStepModel(Base):
  __tablename__ = 'workflow_steps'
  __table_args__ = (UniqueConstraint('instance_id', 'step_number', name='uq_workflow_steps_instance_step'),)

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  instance_id: Mapped[str] = mapped_column(
    String(32), ForeignKey('workflow_instances.id', name='fk_workflow_steps_instance'), index=True, nullable=False
  )
  step_number: Mapped[int] = mapped_column(Integer, nullable=False)
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  assigned_role: Mapped[str] = mapped_column(String(100), nullable=False)
  status: Mapped[str] = mapped_column(String(30), nullable=False, default='PENDING')
  decided_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
  comment: Mapped[str | None] = mapped_column(Text, nullable=True)
  decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  # Phase 2: parallel / conditional / escalation / delegation
  parallel_group_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
  condition: Mapped[str | None] = mapped_column(String(500), nullable=True)
  timeout_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
  escalation_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
  delegation_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  delegated_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
  delegated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

  instance: Mapped[WorkflowInstanceModel] = relationship(back_populates='steps')


class WorkflowHistoryModel(Base):
  __tablename__ = 'workflow_history'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  instance_id: Mapped[str] = mapped_column(
    String(32), ForeignKey('workflow_instances.id', name='fk_workflow_history_instance'), index=True, nullable=False
  )
  from_state: Mapped[str] = mapped_column(String(30), nullable=False)
  to_state: Mapped[str] = mapped_column(String(30), nullable=False)
  actor_id: Mapped[str] = mapped_column(String(32), nullable=False)
  reason: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

  instance: Mapped[WorkflowInstanceModel] = relationship(back_populates='history')
