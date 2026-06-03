from __future__ import annotations

import uuid
from dataclasses import dataclass


class TenantContextError(ValueError):
    """Raised when tenant context is absent or malformed."""


@dataclass(frozen=True, slots=True)
class TenantContext:
    tenant_id: uuid.UUID


def ensure_tenant_context(tenant_id: uuid.UUID | str | None) -> TenantContext:
    if tenant_id is None:
        raise TenantContextError("tenant_id is required")

    try:
        resolved_tenant_id = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    except ValueError as exc:
        raise TenantContextError("tenant_id must be a valid UUID") from exc

    return TenantContext(tenant_id=resolved_tenant_id)
