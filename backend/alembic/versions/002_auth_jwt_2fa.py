"""auth jwt 2fa

Revision ID: 002_auth_jwt_2fa
Revises: 001_tenant
Create Date: 2026-06-02 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_auth_jwt_2fa"
down_revision = "001_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_auth_user_tenant_email"),
    )
    op.create_index(op.f("ix_auth_user_email"), "auth_user", ["email"], unique=False)
    op.create_index(op.f("ix_auth_user_tenant_id"), "auth_user", ["tenant_id"], unique=False)

    op.create_table(
        "auth_refresh_session",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["replaced_by_session_id"], ["auth_refresh_session.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_refresh_session_family_id"), "auth_refresh_session", ["family_id"], unique=False)
    op.create_index(op.f("ix_auth_refresh_session_tenant_id"), "auth_refresh_session", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_auth_refresh_session_token_hash"), "auth_refresh_session", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_refresh_session_user_id"), "auth_refresh_session", ["user_id"], unique=False)

    op.create_table(
        "auth_totp_credential",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secret_encrypted", sa.String(length=512), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_auth_totp_credential_tenant_user"),
    )
    op.create_index(op.f("ix_auth_totp_credential_tenant_id"), "auth_totp_credential", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_auth_totp_credential_user_id"), "auth_totp_credential", ["user_id"], unique=False)

    op.create_table(
        "auth_login_challenge",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("challenge_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_login_challenge_challenge_hash"), "auth_login_challenge", ["challenge_hash"], unique=True)
    op.create_index(op.f("ix_auth_login_challenge_tenant_id"), "auth_login_challenge", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_auth_login_challenge_user_id"), "auth_login_challenge", ["user_id"], unique=False)

    op.create_table(
        "auth_password_reset_token",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_password_reset_token_tenant_id"), "auth_password_reset_token", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_auth_password_reset_token_token_hash"), "auth_password_reset_token", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_password_reset_token_user_id"), "auth_password_reset_token", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_password_reset_token_user_id"), table_name="auth_password_reset_token")
    op.drop_index(op.f("ix_auth_password_reset_token_token_hash"), table_name="auth_password_reset_token")
    op.drop_index(op.f("ix_auth_password_reset_token_tenant_id"), table_name="auth_password_reset_token")
    op.drop_table("auth_password_reset_token")

    op.drop_index(op.f("ix_auth_login_challenge_user_id"), table_name="auth_login_challenge")
    op.drop_index(op.f("ix_auth_login_challenge_tenant_id"), table_name="auth_login_challenge")
    op.drop_index(op.f("ix_auth_login_challenge_challenge_hash"), table_name="auth_login_challenge")
    op.drop_table("auth_login_challenge")

    op.drop_index(op.f("ix_auth_totp_credential_user_id"), table_name="auth_totp_credential")
    op.drop_index(op.f("ix_auth_totp_credential_tenant_id"), table_name="auth_totp_credential")
    op.drop_table("auth_totp_credential")

    op.drop_index(op.f("ix_auth_refresh_session_user_id"), table_name="auth_refresh_session")
    op.drop_index(op.f("ix_auth_refresh_session_token_hash"), table_name="auth_refresh_session")
    op.drop_index(op.f("ix_auth_refresh_session_tenant_id"), table_name="auth_refresh_session")
    op.drop_index(op.f("ix_auth_refresh_session_family_id"), table_name="auth_refresh_session")
    op.drop_table("auth_refresh_session")

    op.drop_index(op.f("ix_auth_user_tenant_id"), table_name="auth_user")
    op.drop_index(op.f("ix_auth_user_email"), table_name="auth_user")
    op.drop_table("auth_user")
