"""LLM configuration API endpoints."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models import (
    User, LlmConfig, LlmAdminDefaults, LlmUserAccess, LlmAuditLog,
    LlmProvider, ResponseFormat, AuditAction, RoleEnum
)
from app.services.llm_service import LlmService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
llm_service = LlmService()


# Request/Response Models
class LlmConfigInput(BaseModel):
    """LLM configuration input."""
    provider: LlmProvider
    model: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)
    base_url: Optional[str] = Field(None, max_length=500)
    region: Optional[str] = Field(None, max_length=50)
    deployment: Optional[str] = Field(None, max_length=100)
    extra_headers: Optional[Dict[str, str]] = None
    response_format: ResponseFormat = ResponseFormat.AUTO
    daily_limit: Optional[int] = Field(None, ge=1, le=10000)


class LlmConfigSummary(BaseModel):
    """LLM configuration summary (no API key)."""
    id: str
    provider: LlmProvider
    model: str
    base_url: Optional[str]
    key_last_four: str
    last_validated_at: Optional[str]
    usage_today: int
    daily_limit: Optional[int]
    is_active: bool
    created_at: str
    updated_at: str


class TestConnectionRequest(BaseModel):
    """Test connection request."""
    provider: LlmProvider
    model: str
    api_key: str
    base_url: Optional[str] = None
    extra_headers: Optional[Dict[str, str]] = None


class TestConnectionResult(BaseModel):
    """Test connection result."""
    ok: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class AdminDefaults(BaseModel):
    """Admin defaults configuration."""
    enforced: bool = False
    default_provider: Optional[LlmProvider] = None
    default_model: Optional[str] = None
    allowed_providers: Optional[List[LlmProvider]] = None
    global_daily_cap: Optional[int] = None
    per_user_daily_cap: Optional[int] = None


class UserLlmRow(BaseModel):
    """User LLM management row."""
    user_id: str
    email: str
    full_name: Optional[str]
    has_config: bool
    provider: Optional[LlmProvider]
    model: Optional[str]
    byok_enabled: bool
    daily_cap: Optional[int]
    usage_today: int
    last_used_at: Optional[str]


class AuditRow(BaseModel):
    """Audit log row."""
    id: str
    user_email: str
    admin_email: Optional[str]
    action: AuditAction
    resource_type: str
    provider: Optional[LlmProvider]
    model: Optional[str]
    success: bool
    error_message: Optional[str]
    created_at: str


# Helper functions
def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent."""
    return request.headers.get("User-Agent")


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role not in [RoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# User endpoints
@router.get("/me", response_model=Optional[LlmConfigSummary])
async def get_my_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's LLM configuration."""
    config = await llm_service.get_config(db, current_user.id)
    
    if not config:
        return None
    
    return LlmConfigSummary(
        id=config.id,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        key_last_four=config.key_last_four,
        last_validated_at=config.last_validated_at.isoformat() if config.last_validated_at else None,
        usage_today=config.usage_today,
        daily_limit=config.daily_limit,
        is_active=config.is_active,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat()
    )


@router.post("/test", response_model=TestConnectionResult)
async def test_connection(
    request: Request,
    test_request: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test LLM API connection."""
    try:
        success, latency_ms, error_msg = await llm_service.test_connection(
            test_request.provider,
            test_request.model,
            test_request.api_key,
            test_request.base_url,
            test_request.extra_headers
        )
        
        # Log test attempt
        await llm_service._log_audit(
            db, current_user.id, AuditAction.TEST, "config",
            provider=test_request.provider, model=test_request.model,
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            success=success, error_message=error_msg
        )
        
        return TestConnectionResult(
            ok=success,
            latency_ms=latency_ms,
            error=error_msg
        )
    
    except Exception as e:
        logger.error(f"Test connection error: {e}")
        return TestConnectionResult(
            ok=False,
            error="Internal server error"
        )


@router.post("/save")
async def save_config(
    request: Request,
    config_input: LlmConfigInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save LLM configuration."""
    try:
        # Check if BYOK is disabled globally
        result = await db.execute(select(LlmAdminDefaults))
        defaults = result.scalar_one_or_none()
        
        if defaults and defaults.enforced:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="BYOK is disabled by administrator"
            )
        
        # Check user-specific BYOK permission
        result = await db.execute(
            select(LlmUserAccess).where(LlmUserAccess.user_id == current_user.id)
        )
        user_access = result.scalar_one_or_none()
        
        if user_access and not user_access.byok_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="BYOK is disabled for your account"
            )
        
        # Validate provider is allowed
        if defaults and defaults.allowed_providers:
            if config_input.provider not in defaults.allowed_providers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Provider {config_input.provider} is not allowed"
                )
        
        # Save configuration
        config = await llm_service.save_config(
            db, current_user.id,
            config_input.provider, config_input.model, config_input.api_key,
            config_input.base_url, config_input.region, config_input.deployment,
            config_input.extra_headers, config_input.response_format,
            config_input.daily_limit,
            get_client_ip(request), get_user_agent(request)
        )
        
        return {"ok": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration"
        )


@router.post("/rotate")
async def rotate_key(
    request: Request,
    new_key_request: dict,  # {"api_key": "new_key"}
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rotate API key."""
    try:
        config = await llm_service.get_config(db, current_user.id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No LLM configuration found"
            )
        
        new_api_key = new_key_request.get("api_key")
        if not new_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New API key is required"
            )
        
        # Test new key first
        success, _, error_msg = await llm_service.test_connection(
            config.provider, config.model, new_api_key,
            config.base_url, config.extra_headers
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"New API key test failed: {error_msg}"
            )
        
        # Update key
        await llm_service.save_config(
            db, current_user.id,
            config.provider, config.model, new_api_key,
            config.base_url, config.region, config.deployment,
            config.extra_headers, config.response_format,
            config.daily_limit,
            get_client_ip(request), get_user_agent(request)
        )
        
        # Log rotation
        await llm_service._log_audit(
            db, current_user.id, AuditAction.ROTATE, "config", config.id,
            provider=config.provider, model=config.model,
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            success=True
        )
        
        return {"ok": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rotate key error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate key"
        )


@router.delete("/me")
async def delete_my_config(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's LLM configuration."""
    try:
        success = await llm_service.delete_config(
            db, current_user.id,
            get_client_ip(request), get_user_agent(request)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No configuration found"
            )
        
        return {"ok": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )


# Admin endpoints
@router.get("/admin/defaults", response_model=AdminDefaults)
async def get_admin_defaults(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin defaults."""
    result = await db.execute(select(LlmAdminDefaults))
    defaults = result.scalar_one_or_none()

    if not defaults:
        return AdminDefaults()

    return AdminDefaults(
        enforced=defaults.enforced,
        default_provider=defaults.default_provider,
        default_model=defaults.default_model,
        allowed_providers=defaults.allowed_providers,
        global_daily_cap=defaults.global_daily_cap,
        per_user_daily_cap=defaults.per_user_daily_cap
    )


@router.post("/admin/defaults")
async def save_admin_defaults(
    request: Request,
    defaults_input: AdminDefaults,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Save admin defaults."""
    try:
        result = await db.execute(select(LlmAdminDefaults))
        defaults = result.scalar_one_or_none()

        if defaults:
            # Update existing
            defaults.enforced = defaults_input.enforced
            defaults.default_provider = defaults_input.default_provider
            defaults.default_model = defaults_input.default_model
            defaults.allowed_providers = defaults_input.allowed_providers
            defaults.global_daily_cap = defaults_input.global_daily_cap
            defaults.per_user_daily_cap = defaults_input.per_user_daily_cap
            defaults.updated_at = datetime.utcnow()
        else:
            # Create new
            defaults = LlmAdminDefaults(
                enforced=defaults_input.enforced,
                default_provider=defaults_input.default_provider,
                default_model=defaults_input.default_model,
                allowed_providers=defaults_input.allowed_providers,
                global_daily_cap=defaults_input.global_daily_cap,
                per_user_daily_cap=defaults_input.per_user_daily_cap
            )
            db.add(defaults)

        await db.commit()

        # Log audit event
        await llm_service._log_audit(
            db, admin_user.id, AuditAction.UPDATE, "defaults", defaults.id,
            admin_user_id=admin_user.id,
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            success=True
        )

        return {"ok": True}

    except Exception as e:
        logger.error(f"Save admin defaults error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save defaults"
        )


@router.get("/admin/users", response_model=Dict[str, Any])
async def get_users(
    page: int = 1,
    limit: int = 50,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get users with LLM configuration info."""
    try:
        offset = (page - 1) * limit

        # Get users with their LLM configs and access settings
        query = (
            select(User, LlmConfig, LlmUserAccess)
            .outerjoin(LlmConfig, User.id == LlmConfig.user_id)
            .outerjoin(LlmUserAccess, User.id == LlmUserAccess.user_id)
            .offset(offset)
            .limit(limit)
            .order_by(User.created_at.desc())
        )

        result = await db.execute(query)
        rows = result.all()

        users = []
        for user, config, access in rows:
            users.append(UserLlmRow(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                has_config=config is not None,
                provider=config.provider if config else None,
                model=config.model if config else None,
                byok_enabled=access.byok_enabled if access else True,
                daily_cap=access.daily_cap if access else None,
                usage_today=config.usage_today if config else 0,
                last_used_at=config.last_used_at.isoformat() if config and config.last_used_at else None
            ))

        # Get total count
        count_query = select(func.count(User.id))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "rows": users,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }

    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )


@router.post("/admin/users/{user_id}/toggle-byok")
async def toggle_user_byok(
    user_id: str,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Toggle BYOK for a user."""
    try:
        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get or create user access
        result = await db.execute(
            select(LlmUserAccess).where(LlmUserAccess.user_id == user_id)
        )
        access = result.scalar_one_or_none()

        if access:
            access.byok_enabled = not access.byok_enabled
            access.updated_at = datetime.utcnow()
        else:
            access = LlmUserAccess(
                user_id=user_id,
                byok_enabled=False  # Default is True, so toggle to False
            )
            db.add(access)

        await db.commit()

        # Log audit event
        action = AuditAction.ENABLE if access.byok_enabled else AuditAction.DISABLE
        await llm_service._log_audit(
            db, user_id, action, "access", access.id,
            admin_user_id=admin_user.id,
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            success=True
        )

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle BYOK error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle BYOK"
        )


@router.post("/admin/users/{user_id}/set-cap")
async def set_user_cap(
    user_id: str,
    cap_request: dict,  # {"daily_cap": 100}
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Set daily cap for a user."""
    try:
        daily_cap = cap_request.get("daily_cap")
        if daily_cap is not None and (daily_cap < 0 or daily_cap > 10000):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Daily cap must be between 0 and 10000"
            )

        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get or create user access
        result = await db.execute(
            select(LlmUserAccess).where(LlmUserAccess.user_id == user_id)
        )
        access = result.scalar_one_or_none()

        if access:
            access.daily_cap = daily_cap
            access.updated_at = datetime.utcnow()
        else:
            access = LlmUserAccess(
                user_id=user_id,
                daily_cap=daily_cap
            )
            db.add(access)

        await db.commit()

        # Log audit event
        await llm_service._log_audit(
            db, user_id, AuditAction.SET_CAP, "access", access.id,
            admin_user_id=admin_user.id,
            new_values={"daily_cap": daily_cap},
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
            success=True
        )

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set user cap error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user cap"
        )


@router.get("/admin/audit", response_model=Dict[str, Any])
async def get_audit_logs(
    page: int = 1,
    limit: int = 50,
    user_id: Optional[str] = None,
    action: Optional[AuditAction] = None,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with filtering."""
    try:
        offset = (page - 1) * limit

        # Build query with filters
        query = (
            select(LlmAuditLog, User.email.label("user_email"))
            .join(User, LlmAuditLog.user_id == User.id)
            .outerjoin(User.alias("admin_user"), LlmAuditLog.admin_user_id == User.alias("admin_user").id)
        )

        if user_id:
            query = query.where(LlmAuditLog.user_id == user_id)
        if action:
            query = query.where(LlmAuditLog.action == action)

        query = query.order_by(desc(LlmAuditLog.created_at)).offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        audit_logs = []
        for log, user_email in rows:
            # Get admin email if admin action
            admin_email = None
            if log.admin_user_id:
                admin_result = await db.execute(
                    select(User.email).where(User.id == log.admin_user_id)
                )
                admin_email = admin_result.scalar_one_or_none()

            audit_logs.append(AuditRow(
                id=log.id,
                user_email=user_email,
                admin_email=admin_email,
                action=log.action,
                resource_type=log.resource_type,
                provider=log.provider,
                model=log.model,
                success=log.success,
                error_message=log.error_message,
                created_at=log.created_at.isoformat()
            ))

        # Get total count
        count_query = select(func.count(LlmAuditLog.id))
        if user_id:
            count_query = count_query.where(LlmAuditLog.user_id == user_id)
        if action:
            count_query = count_query.where(LlmAuditLog.action == action)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        return {
            "rows": audit_logs,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }

    except Exception as e:
        logger.error(f"Get audit logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audit logs"
        )


@router.get("/admin/users/export")
async def export_users_csv(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Export users to CSV."""
    try:
        # Get all users with LLM info
        query = (
            select(User, LlmConfig, LlmUserAccess)
            .outerjoin(LlmConfig, User.id == LlmConfig.user_id)
            .outerjoin(LlmUserAccess, User.id == LlmUserAccess.user_id)
            .order_by(User.created_at.desc())
        )

        result = await db.execute(query)
        rows = result.all()

        # Build CSV content
        csv_lines = [
            "user_id,email,full_name,has_config,provider,model,byok_enabled,daily_cap,usage_today,last_used_at"
        ]

        for user, config, access in rows:
            csv_lines.append(
                f"{user.id},{user.email},{user.full_name or ''},"
                f"{config is not None},{config.provider if config else ''},"
                f"{config.model if config else ''},{access.byok_enabled if access else True},"
                f"{access.daily_cap if access else ''},{config.usage_today if config else 0},"
                f"{config.last_used_at.isoformat() if config and config.last_used_at else ''}"
            )

        csv_content = "\n".join(csv_lines)

        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_llm_export.csv"}
        )

    except Exception as e:
        logger.error(f"Export users CSV error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export users"
        )
