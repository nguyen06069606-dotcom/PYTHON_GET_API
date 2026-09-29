"""Initial schema: products, users, roles and sync audit."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("products", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(120), nullable=False, index=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False), sa.Column("discount_percentage", sa.Numeric(8, 3), nullable=False),
        sa.Column("rating", sa.Numeric(5, 2), nullable=False), sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("brand", sa.String(200)), sa.Column("sku", sa.String(100), nullable=False, index=True),
        sa.Column("thumbnail", sa.Text(), nullable=False), sa.Column("source_updated_at", sa.String(80)),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("sync_runs", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("items_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_inserted_or_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()))

def downgrade() -> None:
    op.drop_table("sync_runs")
    op.drop_table("products")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")

