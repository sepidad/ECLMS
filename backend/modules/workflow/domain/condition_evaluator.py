"""Workflow condition expression evaluation (production hardening).

Phase 2 used Python's built-in `eval` restricted to the ``contract``
object.  That is unsafe for production.  This module evaluates conditional
step expressions with `simpleeval`, which parses the expression into an
AST and evaluates it against an explicit allow-list of names and functions,
so no arbitrary Python can be executed.

Supported (production) syntax mirrors what workflows need:

    - field access:        ``contract.counterparty``, ``contract.state``
    - comparisons:         ``==``, ``!=``, ``>``, ``>=``, ``<``, ``<=``
    - boolean operators:   ``and``, ``or``, ``not``
    - membership:          ``in``, ``not in``
    - string methods:      ``.lower()``, ``.upper()``
    - arithmetic:          ``+``, ``-``, ``*``, ``/``, ``%``

Unknown attributes, unknown names, and any function not on the allow-list
raise ``ConditionEvaluationError``; the caller decides how to handle it
(typically an invalid condition means the step is treated as not-runnable).
"""

from __future__ import annotations

from typing import Any

from simpleeval import EvalWithCompoundTypes, InvalidExpression

from backend.core.exceptions import ECLMSError


class ConditionEvaluationError(ECLMSError):
  """Raised when a workflow condition cannot be parsed or evaluated."""


class ConditionEvaluator:
  """Evaluates a workflow step condition against a context object."""

  def __init__(self) -> None:
    self._allowed_functions = {
      'len': len,
      'abs': abs,
      'min': min,
      'max': max,
      'str': str,
      'lower': lambda s: s.lower() if isinstance(s, str) else s,
      'upper': lambda s: s.upper() if isinstance(s, str) else s,
    }

  def evaluate(self, condition: str | None, context: Any) -> bool:
    """Evaluate ``condition`` against ``context``.

    Returns True when there is no condition (an unconditional step always runs).  A
    non-boolean result (or a parse failure) raises ``ConditionEvaluationError``.
    """
    if not condition:
      return True
    try:
      evaluator = EvalWithCompoundTypes(
        names={'contract': context},
        functions=self._allowed_functions,
      )
      result = evaluator.eval(condition)
    except InvalidExpression as exc:
      raise ConditionEvaluationError(
        f'Invalid workflow condition: {condition}',
        details={'condition': condition, 'error': str(exc)},
      ) from exc
    if not isinstance(result, bool):
      raise ConditionEvaluationError(
        f'Workflow condition did not evaluate to bool: {condition}',
        details={'condition': condition, 'result': repr(result)},
      )
    return result