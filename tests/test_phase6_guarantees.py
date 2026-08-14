from datetime import timedelta

from backend.core.utils import utc_now
from backend.modules.contracts.domain.guarantee import Guarantee


def test_received_guarantee_warning_levels():
  today = utc_now().date()
  item = Guarantee('c', 'performance', 'RECEIVED', 100, 'IRR', 'bank', 'org', 'x', today, today + timedelta(days=7))
  assert item.warning(today) == 'URGENT_EXPIRY'
  assert item.warning(today + timedelta(days=8)) == 'EXPIRED'

def test_issued_guarantee_becomes_release_overdue():
  today = utc_now().date()
  item = Guarantee('c', 'performance', 'ISSUED', 100, 'IRR', 'bank', 'org', 'x', today - timedelta(days=2), today - timedelta(days=1))
  assert item.warning(today) == 'RELEASE_OVERDUE'
