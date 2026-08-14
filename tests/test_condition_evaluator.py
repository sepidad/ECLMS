"""Tests for the production workflow condition evaluator (no eval)."""

import pytest

from backend.modules.workflow.domain.condition_evaluator import (
  ConditionEvaluationError,
  ConditionEvaluator,
)


class _FakeContract:
  def __init__(self, counterparty='Acme', state='DRAFT', value=1000) -> None:
    self.counterparty = counterparty
    self.state = state
    self.value = value


def test_no_condition_runs():
  assert ConditionEvaluator().evaluate(None, _FakeContract()) is True
  assert ConditionEvaluator().evaluate('', _FakeContract()) is True


def test_string_equality():
  ce = ConditionEvaluator()
  assert ce.evaluate("contract.counterparty == 'Acme'", _FakeContract()) is True
  assert ce.evaluate("contract.counterparty == 'Other'", _FakeContract()) is False


def test_comparison_arithmetic():
  ce = ConditionEvaluator()
  assert ce.evaluate('contract.value > 100', _FakeContract()) is True
  assert ce.evaluate('contract.value >= 1000', _FakeContract()) is True
  assert ce.evaluate('contract.value < 100', _FakeContract()) is False


def test_boolean_and_membership():
  ce = ConditionEvaluator()
  assert ce.evaluate("contract.counterparty == 'Acme' and contract.value > 500", _FakeContract()) is True
  assert ce.evaluate("contract.counterparty in ('Acme', 'Globex')", _FakeContract()) is True
  assert ce.evaluate("contract.state == 'APPROVED' or contract.counterparty == 'Acme'", _FakeContract()) is True


def test_string_methods():
  ce = ConditionEvaluator()
  assert ce.evaluate("contract.counterparty.lower() == 'acme'", _FakeContract()) is True


def test_non_boolean_result_rejected():
  ce = ConditionEvaluator()
  with pytest.raises(ConditionEvaluationError):
    ce.evaluate('contract.value', _FakeContract())


def test_unknown_attribute_rejected():
  ce = ConditionEvaluator()
  # Unknown attribute on the contract raises InvalidExpression, treated as error.
  with pytest.raises(ConditionEvaluationError):
    ce.evaluate('contract.no_such_field == 1', _FakeContract())


def test_arbitrary_code_rejected():
  ce = ConditionEvaluator()
  with pytest.raises(ConditionEvaluationError):
    ce.evaluate("__import__('os').system('echo pwned')", _FakeContract())


def test_unsafe_function_rejected():
  ce = ConditionEvaluator()
  with pytest.raises(ConditionEvaluationError):
    ce.evaluate('open("secret").read() == "x"', _FakeContract())
