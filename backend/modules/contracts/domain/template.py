"""Contract template definitions used by the Phase 6 preparation workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateField:
  key: str
  label: str
  required: bool = True


@dataclass(frozen=True)
class ContractTemplate:
  key: str
  name: str
  description: str
  fields: tuple[TemplateField, ...]
  locked_clauses: tuple[str, ...]
  optional_clauses: tuple[str, ...]
  required_guarantees: tuple[str, ...]
  review_sla_hours: dict[str, int]


TEMPLATES: tuple[ContractTemplate, ...] = (
  ContractTemplate(
    key='general-service',
    name='General Service Contract',
    description='Base English template for ordinary services and deliverables.',
    fields=(
      TemplateField('parties', 'Parties'),
      TemplateField('contract_value', 'Contract value'),
      TemplateField('start_date', 'Start date'),
      TemplateField('end_date', 'End date'),
      TemplateField('insurance_percentage', 'Insurance percentage'),
      TemplateField('payment_terms', 'Payment terms'),
    ),
    locked_clauses=('governing-law', 'confidentiality', 'audit-rights'),
    optional_clauses=('price-escalation', 'liquidated-damages'),
    required_guarantees=('performance',),
    review_sla_hours={'LEGAL': 48, 'FINANCE': 24},
  ),
  ContractTemplate(
    key='procurement',
    name='Procurement Contract',
    description='Template for procurement with bid, advance, and performance controls.',
    fields=(
      TemplateField('parties', 'Parties'),
      TemplateField('contract_value', 'Contract value'),
      TemplateField('delivery_date', 'Delivery date'),
      TemplateField('advance_percentage', 'Advance-payment percentage'),
      TemplateField('insurance_percentage', 'Insurance percentage'),
    ),
    locked_clauses=('governing-law', 'confidentiality', 'termination'),
    optional_clauses=('price-escalation', 'delivery-penalties'),
    required_guarantees=('bid-bond', 'advance-payment', 'performance'),
    review_sla_hours={'LEGAL': 48, 'FINANCE': 24},
  ),
)


def list_templates() -> list[dict]:
  return [
    {
      'key': item.key,
      'name': item.name,
      'description': item.description,
      'fields': [field.__dict__ for field in item.fields],
      'locked_clauses': list(item.locked_clauses),
      'optional_clauses': list(item.optional_clauses),
      'required_guarantees': list(item.required_guarantees),
      'review_sla_hours': item.review_sla_hours,
    }
    for item in TEMPLATES
  ]


def get_template(key: str) -> ContractTemplate | None:
  return next((item for item in TEMPLATES if item.key == key), None)
