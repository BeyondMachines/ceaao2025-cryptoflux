"""liquidity table"""

from alembic import op
import sqlalchemy as sa

revision = "20251006_liquidity"
down_revision = "150d02272f8c"  
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "liquidity",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False, index=True),
        sa.Column("window_start_unix", sa.Integer, nullable=False, index=True),
        sa.Column("window_end_unix", sa.Integer, nullable=False, index=True),
        sa.Column("volume_usd", sa.Numeric(24,8), nullable=False, server_default="0"),
        sa.Column("trades_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("liq_score", sa.Numeric(24,8), nullable=False, server_default="0"),
        sa.UniqueConstraint("symbol","window_start_unix","window_end_unix", name="uq_liq_symbol_window"),
    )
    # op.create_index("ix_liquidity_symbol", "liquidity", ["symbol"])
    op.create_index("ix_liquidity_ws", "liquidity", ["window_start_unix"])
    op.create_index("ix_liquidity_we", "liquidity", ["window_end_unix"])
    
def downgrade():
    op.drop_index("ix_liquidity_we", table_name="liquidity")
    op.drop_index("ix_liquidity_ws", table_name="liquidity")
    op.drop_index("ix_liquidity_symbol", table_name="liquidity")
    op.drop_table("liquidity")
