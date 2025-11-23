"""create liquidity_results table"""

from alembic import op
import sqlalchemy as sa

revision = 'liquidity_results'
down_revision = '20251006_liquidity'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'liquidity_results',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('job_id', sa.String(64), nullable=False),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('window_start_unix', sa.Integer, nullable=False),
        sa.Column('window_end_unix', sa.Integer, nullable=False),
        sa.Column('volume_usd', sa.Numeric(24, 8), nullable=False, server_default='0'),
        sa.Column('trades_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('liq_score', sa.Numeric(24, 8), nullable=False, server_default='0'),
        sa.UniqueConstraint(
            'job_id', 'symbol', 'window_start_unix', 'window_end_unix',
            name='uq_liq_job_symbol_window'
        ),
    )
    op.create_index('ix_liq_results_symbol', 'liquidity_results', ['symbol'])
    op.create_index('ix_liq_results_ws', 'liquidity_results', ['window_start_unix'])
    op.create_index('ix_liq_results_we', 'liquidity_results', ['window_end_unix'])

def downgrade():
    op.drop_index('ix_liq_results_we', table_name='liquidity_results')
    op.drop_index('ix_liq_results_ws', table_name='liquidity_results')
    op.drop_index('ix_liq_results_symbol', table_name='liquidity_results')
    op.drop_table('liquidity_results')
