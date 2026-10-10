"""
Database migration script to add data_mode and retention tables to active PostgreSQL instance.
"""
import asyncio
from sqlalchemy import text
from app.core.database import async_engine

MIGRATION_SQL = """
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS data_mode VARCHAR(20) NOT NULL DEFAULT 'demo';
ALTER TABLE risk_assessments ADD COLUMN IF NOT EXISTS data_mode VARCHAR(20) NOT NULL DEFAULT 'demo';

CREATE TABLE IF NOT EXISTS retention_policies (
    module                  VARCHAR(50) PRIMARY KEY,
    retention_period        VARCHAR(20) NOT NULL DEFAULT 'all',
    auto_purge_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    last_purged_at          TIMESTAMP WITH TIME ZONE,
    records_purged_last     INT DEFAULT 0,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO retention_policies (module, retention_period) VALUES
    ('incidents', 'all'),
    ('risk_assessments', 'all')
ON CONFLICT (module) DO NOTHING;

CREATE TABLE IF NOT EXISTS workspace_settings (
    key         VARCHAR(50) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_data_mode ON incidents(data_mode);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_data_mode ON risk_assessments(data_mode);
"""

async def run_migration():
    print("Executing database migration...")
    async with async_engine.begin() as conn:
        for stmt in MIGRATION_SQL.strip().split(";"):
            sql = stmt.strip()
            if sql:
                await conn.execute(text(sql))
    print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
