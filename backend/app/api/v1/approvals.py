"""Approval routes — the human gate.

The founder approves, edits, or rejects. Nothing reaches an employee before a decision
lands here, and every decision records who made it.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import ApprovalSvc, DbSession, FounderUser
from app.models.approval import Approval
from app.models.enums import ApprovalState
from app.schemas.approval import (
    ApprovalDetail,
    ApprovalEditRequest,
    ApprovalListResponse,
    ApprovalRejectRequest,
    ApprovalSummary,
    BulkApproveRequest,
    BulkApproveResponse,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _detail(approval: Approval, service) -> ApprovalDetail:
    detail = ApprovalDetail.model_validate(approval)
    owner_id = approval.task.owner_employee_id
    if owner_id:
        owners = service.employees.get_many([owner_id])
        detail.task.owner_name = owners[0].name if owners else None
    return detail


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    service: ApprovalSvc,
    _: FounderUser,
    state: Annotated[list[ApprovalState] | None, Query()] = None,
) -> ApprovalListResponse:
    """The queue.

    Defaults to everything undecided — which includes *edited*, because editing is not
    deciding. An edited task stays in the queue, visibly touched, until it is approved
    or rejected.
    """
    approvals, total = service.queue(states=state)

    owner_ids = {a.task.owner_employee_id for a in approvals if a.task.owner_employee_id}
    names = {e.id: e.name for e in service.employees.get_many(owner_ids)}

    items = []
    for approval in approvals:
        summary = ApprovalSummary.model_validate(approval)
        summary.task.owner_name = names.get(approval.task.owner_employee_id)
        items.append(summary)

    return ApprovalListResponse(items=items, total=total)


@router.get("/{approval_id}", response_model=ApprovalDetail)
def get_approval(approval_id: uuid.UUID, service: ApprovalSvc, _: FounderUser) -> ApprovalDetail:
    """One approval with the full task, including its verbatim source quote."""
    return _detail(service.get_or_404(approval_id), service)


@router.post("/{approval_id}/approve", response_model=ApprovalDetail)
def approve(
    approval_id: uuid.UUID, service: ApprovalSvc, current_user: FounderUser, db: DbSession
) -> ApprovalDetail:
    """Approve. 409 if it was already decided — re-deciding would rewrite history."""
    approval = service.approve(approval_id, decided_by=current_user)
    db.commit()
    db.refresh(approval)
    return _detail(approval, service)


@router.post("/{approval_id}/edit", response_model=ApprovalDetail)
def edit(
    approval_id: uuid.UUID,
    payload: ApprovalEditRequest,
    service: ApprovalSvc,
    _: FounderUser,
    db: DbSession,
) -> ApprovalDetail:
    """Fix a wrong owner or deadline. The task stays undecided.

    The before/after is kept in edited_payload — that record is what shows whether
    extraction is improving, not just that a human intervened.
    """
    approval = service.edit(approval_id, payload)
    db.commit()
    db.refresh(approval)
    return _detail(approval, service)


@router.post("/{approval_id}/reject", response_model=ApprovalDetail)
def reject(
    approval_id: uuid.UUID,
    payload: ApprovalRejectRequest,
    service: ApprovalSvc,
    current_user: FounderUser,
    db: DbSession,
) -> ApprovalDetail:
    """Reject. The task is marked rejected and nobody is contacted."""
    approval = service.reject(approval_id, decided_by=current_user, reason=payload.reason)
    db.commit()
    db.refresh(approval)
    return _detail(approval, service)


@router.post("/bulk-approve", response_model=BulkApproveResponse)
def bulk_approve(
    payload: BulkApproveRequest,
    service: ApprovalSvc,
    current_user: FounderUser,
    db: DbSession,
) -> BulkApproveResponse:
    """Approve several at once.

    An unknown or already-decided id is reported in `skipped` rather than failing the
    batch — the founder should not lose twenty good approvals to one stale id.
    """
    approved, skipped = service.bulk_approve(payload.approval_ids, decided_by=current_user)
    db.commit()
    return BulkApproveResponse(approved=approved, skipped=skipped)
