from backend.modules.contracts.domain.template import get_template, list_templates


def test_phase6_template_library_exposes_structured_workflow_rules():
  templates = list_templates()

  assert {item['key'] for item in templates} == {'general-service', 'procurement'}
  procurement = get_template('procurement')
  assert procurement is not None
  assert 'insurance_percentage' in {field.key for field in procurement.fields}
  assert procurement.required_guarantees == ('bid-bond', 'advance-payment', 'performance')
  assert procurement.review_sla_hours == {'LEGAL': 48, 'FINANCE': 24}
  assert 'governing-law' in procurement.locked_clauses


def test_unknown_template_is_not_silently_created():
  assert get_template('does-not-exist') is None
