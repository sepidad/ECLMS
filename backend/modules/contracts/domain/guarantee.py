from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.core.utils import new_id, utc_now

GUARANTEE_TYPES = {'bid-bond', 'advance-payment', 'performance', 'insurance', 'other'}
GUARANTEE_DIRECTIONS = {'RECEIVED', 'ISSUED'}


@dataclass
class Guarantee:
  contract_id: str
  guarantee_type: str
  direction: str
  amount: float
  currency: str
  issuer: str
  beneficiary: str
  serial_number: str
  valid_from: date
  expires_on: date
  id: str = ''
  state: str = 'ACTIVE'
  created_at: object = None

  def __post_init__(self):
    if self.guarantee_type not in GUARANTEE_TYPES:
      raise ValueError('Unsupported guarantee type')
    if self.direction not in GUARANTEE_DIRECTIONS:
      raise ValueError('Unsupported guarantee direction')
    if self.amount <= 0:
      raise ValueError('Guarantee amount must be positive')
    if self.expires_on < self.valid_from:
      raise ValueError('Guarantee expiry must not precede its start')
    self.id = self.id or new_id()
    self.created_at = self.created_at or utc_now()

  def warning(self, today: date | None = None) -> str | None:
    today = today or utc_now().date()
    days = (self.expires_on - today).days
    if self.direction == 'RECEIVED':
      if days < 0: return 'EXPIRED'
      if days <= 7: return 'URGENT_EXPIRY'
      if days <= 30: return 'EXPIRY_WARNING'
    elif days < 0:
      return 'RELEASE_OVERDUE'
    return None
