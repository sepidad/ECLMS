"""Create a repeatable Phase 6 demo dataset.

Run inside the API container after migrations:
  python scripts/seed_demo_data.py
All records use stable usernames/reference numbers, so rerunning is safe.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import select

from backend.core.utils import new_id, utc_now
from backend.modules.identity.application.auth_service import hash_password
from infrastructure.database.models.contract_reviews import ContractReviewFeedbackModel
from infrastructure.database.models.contracts import ContractModel, ContractVersionModel
from infrastructure.database.models.guarantees import GuaranteeModel
from infrastructure.database.models.identity import RoleModel, UserModel, UserRoleModel
from infrastructure.database.models.user_permission_overrides import UserPermissionOverrideModel
from infrastructure.database.seed import seed_roles_permissions
from infrastructure.database.session import get_session_factory, init_database


async def main() -> None:
  init_database()
  await seed_roles_permissions()
  async with get_session_factory()() as session:
    roles = {row.name: row for row in (await session.execute(select(RoleModel))).scalars().all()}
    users = {}
    for username, full_name, role in (
      ('demo-manager-1', 'Demo Contract Manager One', 'CONTRACT_MANAGER'),
      ('demo-manager-2', 'Demo Contract Manager Two', 'CONTRACT_MANAGER'),
      ('demo-legal', 'Demo Legal Advisor', 'CONTRACT_MANAGER'),
      ('demo-finance', 'Demo Finance Head', 'CONTRACT_MANAGER'),
      ('demo-viewer', 'Demo Read Only User', 'VIEWER'),
    ):
      user = (await session.execute(select(UserModel).where(UserModel.username == username))).scalar_one_or_none()
      if user is None:
        user = UserModel(id=new_id(), username=username, email=f'{username}@example.com', full_name=full_name, password_hash=hash_password('Demo12345!'), organization_id='org-default', created_at=utc_now(), updated_at=utc_now())
        session.add(user)
        await session.flush()
      if not any(item.role_id == roles[role].id for item in (await session.execute(select(UserRoleModel).where(UserRoleModel.user_id == user.id))).scalars().all()):
        session.add(UserRoleModel(user_id=user.id, role_id=roles[role].id))
      users[username] = user

    # Manager 2 demonstrates a per-user restriction without changing Manager 1.
    finance_update = 'finance.update'
    override = await session.get(UserPermissionOverrideModel, (users['demo-manager-2'].id, finance_update))
    if override is None:
      session.add(UserPermissionOverrideModel(user_id=users['demo-manager-2'].id, permission_id=finance_update, enabled=False))

    contracts = {}
    states = [('demo-draft', 'Draft contract', 'DRAFT'), ('demo-review', 'Contract awaiting review', 'UNDER_REVIEW'), ('demo-approved', 'Approved contract', 'APPROVED'), ('demo-active', 'Active contract', 'ACTIVE'), ('demo-rejected', 'Returned contract', 'REJECTED')]
    for reference, title, state in states:
      contract = (await session.execute(select(ContractModel).where(ContractModel.reference_number == reference))).scalar_one_or_none()
      if contract is None:
        contract = ContractModel(id=new_id(), title=title, reference_number=reference, counterparty='Demo Supplier Co.', state=state, organization_id='org-default', owner_id=users['demo-manager-1'].id, created_at=utc_now(), updated_at=utc_now())
        session.add(contract)
        await session.flush()
        version = ContractVersionModel(id=new_id(), contract_id=contract.id, version_number=1, title=title, counterparty=contract.counterparty, content=f'{title}\nParties: Demo Organization and Demo Supplier Co.', is_active=True, created_by=contract.owner_id, created_at=utc_now())
        session.add(version)
        await session.flush()
        contract.current_version_id = version.id
      contracts[reference] = contract

    rich_content = {
      'demo-draft': '''GENERAL SERVICE CONTRACT\n\nParties: Demo Organization (Employer) and Demo Supplier Co. (Contractor).\nContract value: 2,500,000,000 IRR.\nTerm: 2026-09-01 to 2027-08-31.\nScope: supply, installation, commissioning, and twelve months of support for the contract management platform.\nPayment: 20% advance against advance-payment guarantee; 60% against approved milestones; 20% after provisional acceptance.\nInsurance: 7% social-security insurance deduction from eligible invoices. VAT and statutory deductions apply.\nPerformance guarantee: 10% of contract value, valid through the warranty period.\nDelivery: milestone 1 design, milestone 2 implementation, milestone 3 acceptance.\nPenalties: 0.2% of the delayed milestone value per week, capped at 10% of contract value.\nTermination: either party may terminate for material breach after 30 days written notice and an opportunity to cure.\nConfidentiality, audit rights, governing law, dispute resolution, force majeure, and data protection clauses apply.\nRequired attachments: commercial offer, tax certificate, insurance certificate, bank guarantee original, implementation plan.''',
      'demo-review': '''PROCUREMENT CONTRACT — UNDER REVIEW\n\nEmployer: Demo Organization. Contractor: Demo Supplier Co.\nReference: DEMO-REVIEW-2026. Total value: 8,750,000,000 IRR.\nDuration: 2026-10-01 through 2028-03-31.\nAdvance payment: 25% after receipt and validation of an advance-payment guarantee.\nPayment schedule: 25% advance, 25% after delivery, 30% after commissioning, 20% after final acceptance.\nInsurance percentage: 7%. Finance must confirm the applicable deduction and tax treatment.\nGuarantees: bid bond, advance-payment guarantee, and performance guarantee equal to 10% of contract value.\nLegal review points: liability cap, termination notice, governing law, confidentiality, subcontracting, and dispute escalation.\nFinancial review points: currency, payment deadlines, late-payment penalty, price escalation, budget code, tax withholding, and cash-flow exposure.\nOpen review items: legal suggested a clearer termination notice; finance requested confirmation of the insurance percentage.\nApproval route: Finance Manager and Unit Manager, followed by Executive Approval.''',
      'demo-approved': '''APPROVED PROCUREMENT CONTRACT\n\nParties: Demo Organization and Demo Supplier Co.\nValue: 18,400,000,000 IRR. Term: 2026-07-01 to 2027-06-30.\nScope: enterprise hardware procurement, delivery, installation, acceptance testing, and warranty support.\nPayment milestones: 20% advance, 40% delivery, 30% commissioning, 10% final acceptance.\nInsurance deduction: 7% of applicable labor and service components. VAT is payable against valid invoices.\nGuarantees: advance-payment guarantee for 20%; performance guarantee for 10%; insurance guarantee through the coverage period.\nAcceptance: provisional acceptance follows successful testing; final acceptance follows twelve months warranty.\nPenalties: delivery delay penalty capped at 10%; repeated failure permits termination.\nApproval: approved by Finance Manager, Unit Manager, and Executive Authority.\nExecution prerequisites: signed original, guarantee originals, insurance certificate, tax clearance, and approved implementation schedule.''',
      'demo-active': '''ACTIVE EXECUTED SERVICE CONTRACT\n\nEmployer: Demo Organization. Contractor: Demo Supplier Co.\nValue: 42,000,000,000 IRR. Effective date: 2026-01-15. Expiry date: 2027-12-31.\nScope: operation and support of mission-critical contract workflows, notifications, reporting, and backup services.\nService levels: critical incidents acknowledged within 30 minutes and resolved within 4 hours; monthly availability target 99.5%.\nPayments: monthly service invoices payable within 30 days after acceptance of the service report.\nInsurance: 7% statutory insurance treatment on eligible services.\nGuarantees: performance guarantee remains valid through the warranty and handover period; issued guarantees require release tracking.\nObligations: monthly performance report, quarterly security review, annual disaster-recovery test, and contract manager renewal review.\nChange control: amendments must revalidate linked guarantees and approval thresholds.\nTermination: material breach, persistent SLA failure, insolvency, or unauthorized disclosure after notice and cure period.''',
      'demo-rejected': '''RETURNED CONTRACT FOR CORRECTION\n\nParties: Demo Organization and Demo Supplier Co.\nValue: 1,200,000,000 IRR. Proposed term: 2026-11-01 to 2027-04-30.\nReason returned: missing insurance percentage, incomplete payment schedule, no performance guarantee attachment, and unclear acceptance criteria.\nManager actions required: complete structured financial fields, attach the required guarantee, clarify delivery milestones, and resubmit for parallel Legal and Finance review.\nDraft clauses: scope, payment, insurance, confidentiality, liability, termination, dispute resolution, audit rights, and document checklist.''',
    }
    for reference, content in rich_content.items():
      version = (await session.execute(select(ContractVersionModel).where(ContractVersionModel.id == contracts[reference].current_version_id))).scalar_one()
      version.content = content

    today = utc_now().date()
    guarantees = [('demo-review', 'performance', 'RECEIVED', 30), ('demo-approved', 'advance-payment', 'RECEIVED', 7), ('demo-active', 'insurance', 'RECEIVED', -1), ('demo-active', 'performance', 'ISSUED', -5), ('demo-draft', 'bid-bond', 'RECEIVED', 90)]
    for reference, kind, direction, days in guarantees:
      serial = f'demo-{reference}-{kind}-{direction}'
      exists = (await session.execute(select(GuaranteeModel).where(GuaranteeModel.serial_number == serial))).scalar_one_or_none()
      if exists is None:
        session.add(GuaranteeModel(id=new_id(), contract_id=contracts[reference].id, guarantee_type=kind, direction=direction, amount=1000000, currency='IRR', issuer='Demo Bank', beneficiary='Demo Organization', serial_number=serial, valid_from=today - timedelta(days=30), expires_on=today + timedelta(days=days), state='ACTIVE', created_at=utc_now()))

    feedback_exists = (await session.execute(select(ContractReviewFeedbackModel).where(ContractReviewFeedbackModel.body == 'Demo legal suggested edit'))).scalar_one_or_none()
    if feedback_exists is None:
      session.add(ContractReviewFeedbackModel(id=new_id(), contract_id=contracts['demo-review'].id, version_id=contracts['demo-review'].current_version_id, reviewer_id=users['demo-legal'].id, reviewer_role='LEGAL', kind='SUGGESTION', body='Demo legal suggested edit', proposed_text='Add a clear termination notice period.', status='OPEN', created_at=utc_now()))
      session.add(ContractReviewFeedbackModel(id=new_id(), contract_id=contracts['demo-review'].id, version_id=contracts['demo-review'].current_version_id, reviewer_id=users['demo-finance'].id, reviewer_role='FINANCE', kind='COMMENT', body='Demo finance comment about insurance percentage.', status='OPEN', created_at=utc_now()))
    await session.commit()
  print('Demo data ready. Password for all demo users: Demo12345!')


if __name__ == '__main__':
  asyncio.run(main())
