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

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id                  VARCHAR(50) PRIMARY KEY,
    action              VARCHAR(100) NOT NULL,
    scope               VARCHAR(100) NOT NULL,
    reason              TEXT NOT NULL,
    records_affected    INT DEFAULT 0,
    performed_by        VARCHAR(100) NOT NULL,
    performed_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata_json       JSONB
);

CREATE INDEX IF NOT EXISTS idx_incidents_data_mode ON incidents(data_mode);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_data_mode ON risk_assessments(data_mode);

CREATE TABLE IF NOT EXISTS causal_edge_calibrations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_service          VARCHAR(100) NOT NULL,
    target_service          VARCHAR(100) NOT NULL,
    dependency_type         VARCHAR(50) NOT NULL DEFAULT 'SYNC',
    causal_strength         FLOAT NOT NULL DEFAULT 0.50,
    propagation_delay_ms    FLOAT NOT NULL DEFAULT 120.0,
    provenance              VARCHAR(30) NOT NULL DEFAULT 'DECLARED',
    confidence              FLOAT NOT NULL DEFAULT 0.50,
    repeatability           FLOAT NOT NULL DEFAULT 0.50,
    experiment_count        INT NOT NULL DEFAULT 0,
    is_declared             BOOLEAN NOT NULL DEFAULT TRUE,
    did_effect_size         FLOAT NOT NULL DEFAULT 0.0,
    p_value_estimate        FLOAT NOT NULL DEFAULT 0.05,
    evidence_summary        TEXT,
    historical_effect_sizes JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_json           JSONB,
    last_calibrated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_causal_edge_source_target UNIQUE (source_service, target_service)
);

CREATE TABLE IF NOT EXISTS causal_experiment_records (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id           VARCHAR(100) UNIQUE NOT NULL,
    target_service          VARCHAR(100) NOT NULL,
    control_service         VARCHAR(100) NOT NULL DEFAULT 'auth-service',
    fault_type              VARCHAR(50) NOT NULL DEFAULT 'latency',
    intensity               FLOAT NOT NULL DEFAULT 0.8,
    duration_seconds        INT NOT NULL DEFAULT 30,
    environment             VARCHAR(50) NOT NULL DEFAULT 'demo',
    status                  VARCHAR(30) NOT NULL DEFAULT 'COMPLETED',
    started_at              TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at                TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_elapsed_seconds FLOAT NOT NULL DEFAULT 0.0,
    injected_by             VARCHAR(100),
    baseline_metrics        JSONB NOT NULL DEFAULT '{}'::jsonb,
    treatment_metrics       JSONB NOT NULL DEFAULT '{}'::jsonb,
    recovery_metrics        JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_impacts        JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_audit            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_causal_edge_source ON causal_edge_calibrations(source_service);
CREATE INDEX IF NOT EXISTS idx_causal_edge_target ON causal_edge_calibrations(target_service);
CREATE INDEX IF NOT EXISTS idx_causal_exp_target ON causal_experiment_records(target_service);

CREATE TABLE IF NOT EXISTS dry_run_simulations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id             UUID REFERENCES incidents(id) ON DELETE SET NULL,
    service_name            VARCHAR(100) NOT NULL,
    environment             VARCHAR(50) NOT NULL DEFAULT 'production',
    baseline_metrics        JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_actions       JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_action      VARCHAR(100) NOT NULL,
    recommendation_reason   TEXT,
    assumptions             JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations             JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_version           VARCHAR(50) NOT NULL DEFAULT 'CounterfactualQueueingTwin-v1.2',
    is_simulated            BOOLEAN NOT NULL DEFAULT TRUE,
    executed_action         VARCHAR(100),
    executed_at             TIMESTAMP WITH TIME ZONE,
    executed_by             UUID REFERENCES users(id) ON DELETE SET NULL,
    executed_by_username    VARCHAR(100),
    remediation_record_id   UUID,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dry_run_service ON dry_run_simulations(service_name);
CREATE INDEX IF NOT EXISTS idx_dry_run_incident ON dry_run_simulations(incident_id);
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
