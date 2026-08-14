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
  contract_type: str
  description: str
  content_template: str
  fields: tuple[TemplateField, ...]
  locked_clauses: tuple[str, ...]
  optional_clauses: tuple[str, ...]
  required_guarantees: tuple[str, ...]
  review_sla_hours: dict[str, int]


TEMPLATES: tuple[ContractTemplate, ...] = (
  ContractTemplate(
    key='general-service',
    name='General Service Contract',
    contract_type='SERVICE',
    description='Base English template for ordinary services and deliverables.',
    content_template='''GENERAL SERVICE CONTRACT\n\n1. PARTIES\nEmployer: [Employer legal name]\nContractor: [Contractor legal name]\n\n2. SUBJECT AND SCOPE\n[Describe the services, deliverables, location, and acceptance criteria.]\n\n3. TERM AND MILESTONES\nStart date: [YYYY-MM-DD]\nEnd date: [YYYY-MM-DD]\nMilestones: [List milestone, due date, and acceptance evidence.]\n\n4. PRICE AND PAYMENT\nContract value: [Amount] [Currency]\nPayment terms: [Advance / milestone / final payment]\n\n5. TAX, INSURANCE, AND DEDUCTIONS\nInsurance percentage: [__%]\nVAT, statutory deductions, retention, and penalties apply as stated in the approved contract data.\n\n6. GUARANTEES\nPerformance guarantee: [Amount / percentage, issuer, expiry, release condition]\n\n7. GOVERNANCE\nThe parties will maintain records, notices, changes, confidentiality, dispute resolution, termination, and governing-law provisions.''',
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
    contract_type='PURCHASE',
    description='Template for procurement with bid, advance, and performance controls.',
    content_template='''PROCUREMENT CONTRACT\n\n1. BUYER AND SELLER\nBuyer: [Buyer legal name]\nSeller: [Seller legal name]\n\n2. GOODS AND TECHNICAL SPECIFICATION\nItem / model / quantity / unit: [Complete schedule]\nStandards and country of origin: [Details]\n\n3. DELIVERY, INSPECTION, AND ACCEPTANCE\nDelivery location: [Location]\nDelivery deadline: [YYYY-MM-DD]\nInspection and acceptance test: [Method and responsible party]\n\n4. PRICE AND PAYMENT\nUnit price: [Amount]\nTotal price: [Amount] [Currency]\nPayment: [Advance / delivery / acceptance]\n\n5. TAX, INSURANCE, AND WARRANTY\nInsurance percentage: [__%]\nWarranty period: [Months]\nDefective goods: repair, replacement, or rejection procedure applies.\n\n6. SECURITIES AND DELAY\nBid bond: [Details]\nAdvance-payment guarantee: [Details]\nPerformance guarantee: [Details]\nDelay damages: [Rate and cap].''',
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
  ContractTemplate(
    key='construction', name='Construction / Works Contract', contract_type='CONSTRUCTION',
    description='Works model with scope breakdown, BOQ, milestones, acceptance, variation, and delay controls.',
    content_template='''CONSTRUCTION / WORKS CONTRACT\n\n1. PARTIES AND PROJECT\nEmployer: [Name]\nContractor: [Name]\nSite: [Location]\n\n2. SCOPE OF WORK\nCivil: [Excavation / foundation / structure / finishing]\nMechanical: [HVAC / plumbing / fire protection]\nElectrical: [Power / lighting / data]\n\n3. PRICE, BOQ, AND PROGRAMME\nPricing method: [Lump sum / unit rate]\nContract price: [Amount] [Currency]\nCompletion date: [YYYY-MM-DD]\nKey milestones and BOQ are attached.\n\n4. QUALITY, TESTING, AND TAKING-OVER\nInspection, testing, defects correction, provisional acceptance, and final acceptance procedure.\n\n5. VARIATIONS, DELAY, AND CLAIMS\nWritten change order required for scope, price, or time changes. Delay event, responsibility, extension of time, and liquidated damages must be recorded.\n\n6. SECURITIES AND CLOSEOUT\nPerformance security, advance security, retention / defects security, as-built documents, warranties, and release conditions.''',
    fields=(TemplateField('parties', 'Parties'), TemplateField('project_site', 'Project site'), TemplateField('contract_price', 'Contract price'), TemplateField('completion_date', 'Completion date'), TemplateField('boq', 'BOQ / schedule')),
    locked_clauses=('governing-law', 'variation-control', 'delay-damages', 'acceptance'), optional_clauses=('price-adjustment', 'subcontracting'), required_guarantees=('performance', 'advance-payment', 'defects'), review_sla_hours={'LEGAL': 72, 'FINANCE': 48},
  ),
  ContractTemplate(
    key='consulting', name='Consulting Services Contract', contract_type='CONSULTING',
    description='Deliverable-based model for professional services, key personnel, review cycles, and IP.',
    content_template='''CONSULTING SERVICES CONTRACT\n\n1. PARTIES AND ASSIGNMENT\nClient: [Name]\nConsultant: [Name]\nAssignment: [Purpose and background]\n\n2. SERVICES AND DELIVERABLES\nD1: [Description, format, due date, reviewer, acceptance criteria]\nD2: [Description, format, due date, reviewer, acceptance criteria]\n\n3. PERSONNEL AND EFFORT\nKey personnel: [Names / qualifications]\nLevel of effort: [Person-months / hours]\n\n4. FEES AND PAYMENT\nFee basis: [Lump sum / time and materials]\nPayment follows accepted deliverables and approved invoices.\n\n5. CONFIDENTIALITY, DATA, AND IP\nConfidential information, work product ownership, licence rights, data protection, and return/destruction obligations.\n\n6. REVIEW, LIABILITY, AND TERMINATION\nReview cycles, professional standard, liability limits, dispute resolution, and termination consequences.''',
    fields=(TemplateField('parties', 'Parties'), TemplateField('assignment', 'Assignment'), TemplateField('deliverables', 'Deliverables'), TemplateField('key_personnel', 'Key personnel'), TemplateField('fee_basis', 'Fee basis')),
    locked_clauses=('confidentiality', 'intellectual-property', 'deliverable-acceptance'), optional_clauses=('travel-expenses', 'publication-rights'), required_guarantees=(), review_sla_hours={'LEGAL': 48, 'FINANCE': 24},
  ),
  ContractTemplate(
    key='maintenance-sla', name='Maintenance and SLA Contract', contract_type='MAINTENANCE',
    description='Operational service model with measurable SLA/KPI, incidents, response times, and service credits.',
    content_template='''MAINTENANCE AND SLA CONTRACT\n\n1. SERVICE\nCustomer: [Name]\nProvider: [Name]\nCovered assets / locations: [List]\n\n2. SERVICE LEVELS\nAvailability target: [__%]\nCritical response: [__ minutes]\nRepair / restoration target: [__ hours]\nPreventive maintenance completion: [__%]\n\n3. SERVICE REQUESTS AND REPORTING\nTicket priority, escalation path, monthly report, measurement method, and customer review.\n\n4. PRICE AND SERVICE CREDITS\nFixed fee / unit fee: [Amount]\nService credits or penalties apply when an agreed KPI is missed, subject to the stated cap.\n\n5. PERSONNEL, SPARES, AND SAFETY\nStaffing, spare parts, access, health and safety, confidentiality, and business continuity.\n\n6. TERM AND EXIT\nRenewal, transition assistance, data return, termination, and final acceptance.''',
    fields=(TemplateField('parties', 'Parties'), TemplateField('covered_assets', 'Covered assets'), TemplateField('sla_kpis', 'SLA / KPIs'), TemplateField('response_times', 'Response times'), TemplateField('service_fee', 'Service fee')),
    locked_clauses=('service-levels', 'reporting', 'termination'), optional_clauses=('service-credits', 'spare-parts'), required_guarantees=(), review_sla_hours={'LEGAL': 48, 'FINANCE': 24},
  ),
)


def list_templates() -> list[dict]:
  return [
    {
      'key': item.key,
      'name': item.name,
      'contract_type': item.contract_type,
      'description': item.description,
      'content_template': item.content_template,
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
