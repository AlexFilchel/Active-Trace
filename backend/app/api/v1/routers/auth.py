from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthenticatedUser, get_current_user, get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginChallengeVerifyRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TotpVerifyRequest,
)
from app.services.auth import AuthService, AuthServiceError, InMemoryLoginRateLimiter, NullRecoveryDelivery, utc_now


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host


def _build_auth_service(*, request: Request, db: AsyncSession) -> AuthService:
    return AuthService(
        session=db,
        rate_limiter=getattr(request.app.state, "login_rate_limiter", InMemoryLoginRateLimiter()),
        recovery_delivery=getattr(request.app.state, "recovery_delivery", NullRecoveryDelivery()),
        now_provider=getattr(request.app.state, "now_provider", None) or utc_now,
    )


def _raise_http_error(error: AuthServiceError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.detail)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    service = _build_auth_service(request=request, db=db)
    try:
        return await service.login(
            email=payload.email,
            password=payload.password,
            ip_address=_client_ip(request),
            tenant_slug=payload.tenant_slug,
        )
    except AuthServiceError as exc:
        _raise_http_error(exc)


@router.post("/refresh")
async def refresh(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    service = _build_auth_service(request=request, db=db)
    try:
        return await service.refresh(refresh_token=payload.refresh_token)
    except AuthServiceError as exc:
        _raise_http_error(exc)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = _build_auth_service(request=request, db=db)
    try:
        await service.logout(
            current_user_id=current_user.user_id,
            current_tenant_id=current_user.tenant_id,
            refresh_token=payload.refresh_token,
        )
    except AuthServiceError as exc:
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/2fa/enroll")
async def enroll_totp(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = _build_auth_service(request=request, db=db)
    try:
        return await service.begin_totp_enrollment(
            current_user_id=current_user.user_id,
            current_tenant_id=current_user.tenant_id,
            email=current_user.email or str(current_user.user_id),
        )
    except AuthServiceError as exc:
        _raise_http_error(exc)


@router.post("/2fa/verify-enrollment")
async def verify_totp_enrollment(
    payload: TotpVerifyRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    service = _build_auth_service(request=request, db=db)
    try:
        return await service.verify_totp_enrollment(
            current_user_id=current_user.user_id,
            current_tenant_id=current_user.tenant_id,
            code=payload.code,
        )
    except AuthServiceError as exc:
        _raise_http_error(exc)


@router.post("/2fa/verify-login")
async def verify_login_totp(
    payload: LoginChallengeVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    service = _build_auth_service(request=request, db=db)
    try:
        return await service.verify_login_2fa(challenge_token=payload.challenge_token, code=payload.code)
    except AuthServiceError as exc:
        _raise_http_error(exc)


@router.post("/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    service = _build_auth_service(request=request, db=db)
    return await service.forgot_password(email=payload.email)


@router.post("/reset")
async def reset_password(payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    service = _build_auth_service(request=request, db=db)
    try:
        return await service.reset_password(token=payload.token, new_password=payload.new_password)
    except AuthServiceError as exc:
        _raise_http_error(exc)
