"""Document API routes.

    POST   /api/v1/documents/upload                    (document.upload)
    GET    /api/v1/documents/contract/{contract_id}    (document.read)

Controllers only validate and delegate to the application layer.
Authorization is enforced by the shared RBAC guards.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response

from backend.api.middleware.context import get_trace_id
from backend.api.responses import err, ok
from backend.api.security import require_permission
from backend.core.exceptions import ECLMSError
from backend.modules.documents.application.document_service import DocumentService

router = APIRouter(tags=['documents'])


def _service(request: Request) -> DocumentService:
  return request.app.state.container.get_service('documents.service')


@router.post('/upload')
async def upload_document(
  request: Request,
  contract_id: str = Form(...),
  file: UploadFile = File(...),  # noqa: B008 - FastAPI dependency injection
  doc_type: str = Form('attachment'),
):
  try:
    actor = await require_permission(request, 'document.upload')
    content = await file.read()
    result = await _service(request).upload(
      contract_id=contract_id,
      file_name=file.filename or 'unnamed',
      content=content,
      doc_type=doc_type,
      organization_id=actor.organization_id,
      created_by=actor.id,
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok(result, get_trace_id())


@router.get('/contract/{contract_id}')
async def list_documents(contract_id: str, request: Request):
  try:
    actor = await require_permission(request, 'document.read')
    items = await _service(request).list_for_contract(contract_id, organization_id=actor.organization_id)
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  return ok({'items': items}, get_trace_id())


@router.get('/{document_id}/download')
async def download_document(document_id: str, request: Request):
  try:
    actor = await require_permission(request, 'document.read')
    content, file_name = await _service(request).get_content(
      document_id, organization_id=actor.organization_id
    )
  except ECLMSError as exc:
    return err(exc.code, exc.message, get_trace_id(), exc.details)
  disposition = f'attachment; filename="{quote(file_name)}"'
  return Response(
    content=content,
    media_type='application/octet-stream',
    headers={'Content-Disposition': disposition},
  )
