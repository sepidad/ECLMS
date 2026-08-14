import pytest

from backend.modules.contracts.application.review_service import ContractReviewService


class FakeContract:
  id = 'contract-1'
  current_version_id = 'version-1'
  state = 'DRAFT'


class FakeContracts:
  def __init__(self):
    self.updated_content = None

  async def get_contract(self, contract_id, *, organization_id):
    return FakeContract()

  async def update_contract(self, contract_id, *, content, organization_id):
    self.updated_content = content
    FakeContract.current_version_id = 'version-2'
    return FakeContract()


class FakeReviews:
  def __init__(self):
    self.status = 'OPEN'

  async def get(self, feedback_id):
    return {'id': feedback_id, 'contract_id': 'contract-1', 'version_id': 'version-1', 'status': self.status}

  async def decide(self, feedback_id, status):
    self.status = status
    return True


@pytest.mark.asyncio
async def test_manager_merge_creates_new_official_version_and_closes_feedback():
  contracts = FakeContracts()
  reviews = FakeReviews()
  service = ContractReviewService(reviews, contracts)

  result = await service.merge(
    contract_id='contract-1', feedback_id='feedback-1',
    new_content='manager-approved-content', organization_id='org-1',
  )

  assert result.current_version_id == 'version-2'
  assert contracts.updated_content == 'manager-approved-content'
  assert reviews.status == 'ACCEPTED'
