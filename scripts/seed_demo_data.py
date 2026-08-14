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
