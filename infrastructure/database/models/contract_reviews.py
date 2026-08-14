from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.session import Base


class ContractReviewFeedbackModel(Base):
  __tablename__ = 'contract_review_feedback'

  id: Mapped[str] = mapped_column(String(32), primary_key=True)
  contract_id: Mapped[str] = mapped_column(String(32), ForeignKey('contracts.id'), index=True, nullable=False)
  version_id: Mapped[str] = mapped_column(String(32), ForeignKey('contract_versions.id'), index=True, nullable=False)
  reviewer_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
  reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
  kind: Mapped[str] = mapped_column(String(24), nullable=False)
  body: Mapped[str] = mapped_column(Text, nullable=False)
  proposed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
  status: Mapped[str] = mapped_column(String(24), nullable=False, default='OPEN', index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
