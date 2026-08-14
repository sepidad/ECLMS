"""Unit tests for the contract lifecycle state machine."""

import pytest

from backend.core.exceptions import StateTransitionError
from backend.modules.contracts.domain.contract import Contract


def _contract() -> Contract:
  return Contract(
    title='Test',
    reference_number='REF-1',
    counterparty='ACME',
    organization_id='org-default',
    owner_id='admin',
  )


def test_new_contract_starts_in_draft():
  assert _contract().state == 'DRAFT'


@pytest.mark.parametrize(
  'transitions,expected',
  [
    (['SUBMITTED'], 'SUBMITTED'),
    (['SUBMITTED', 'UNDER_REVIEW'], 'UNDER_REVIEW'),
    (['SUBMITTED', 'UNDER_REVIEW', 'APPROVED'], 'APPROVED'),
    (['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'EXECUTED'], 'EXECUTED'),
    (['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'EXECUTED', 'ACTIVE'], 'ACTIVE'),
  ],
)
def test_valid_lifecycle_transitions(transitions, expected):
  contract = _contract()
  for state in transitions:
    contract.transition_to(state)
  assert contract.state == expected


def test_rejected_transition_raises():
  contract = _contract()
  with pytest.raises(StateTransitionError):
    contract.transition_to('APPROVED')


def test_no_bypass_of_states():
  contract = _contract()
  contract.transition_to('SUBMITTED')
  with pytest.raises(StateTransitionError):
    contract.transition_to('ACTIVE')
