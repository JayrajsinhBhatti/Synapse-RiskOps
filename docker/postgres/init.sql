-- =====================================================
-- Synapse RiskOps - PostgreSQL Initialization Script
-- =====================================================
-- This script runs automatically when the PostgreSQL
-- container starts for the first time.
-- It creates the database schema and initial seed data.
-- =====================================================

-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100),
    role            VARCHAR(20) NOT NULL DEFAULT 'ENGINEER',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- SERVICES TABLE (for dependency graph)
-- =====================================================
CREATE TABLE IF NOT EXISTS services (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name    VARCHAR(100) UNIQUE NOT NULL,
    service_type    VARCHAR(50) NOT NULL DEFAULT 'MICROSERVICE',
    description     TEXT,
    owner           VARCHAR(100),
    criticality     VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- SERVICE DEPENDENCIES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS service_dependencies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_service_id   UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    target_service_id   UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    dependency_type     VARCHAR(50) NOT NULL DEFAULT 'SYNC',
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(source_service_id, target_service_id)
);

-- =====================================================
-- INCIDENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS incidents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title               VARCHAR(255) NOT NULL,
    description         TEXT,
    severity            VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status              VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    service_id          UUID REFERENCES services(id),
    risk_score          DECIMAL(5,2),
    confidence          DECIMAL(5,4),
    predicted_failure   TIMESTAMP WITH TIME ZONE,
    risk_tier           VARCHAR(20),
    anomaly_score       DECIMAL(10,6),
    forecast_risk       DECIMAL(10,6),
    predicted_failure_type VARCHAR(100),
    root_cause          TEXT,
    guidance            TEXT,
    routing_decision    VARCHAR(50),
    top_features        JSONB,
    affected_services   JSONB,
    data_mode           VARCHAR(20) NOT NULL DEFAULT 'demo',
    detected_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at         TIMESTAMP WITH TIME ZONE,
    assigned_to         UUID REFERENCES users(id),
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INCIDENT HISTORY TABLE (audit trail)
-- =====================================================
CREATE TABLE IF NOT EXISTS incident_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id     UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    action          VARCHAR(50) NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_by      UUID REFERENCES users(id),
    changed_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- RISK ASSESSMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS risk_assessments (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_id              UUID NOT NULL REFERENCES services(id),
    risk_score              DECIMAL(5,2) NOT NULL,
    confidence              DECIMAL(5,4) NOT NULL,
    anomaly_score           DECIMAL(10,6),
    predicted_failure_time  TIMESTAMP WITH TIME ZONE,
    affected_services       TEXT[],
    features_used           JSONB,
    model_version           VARCHAR(50),
    data_mode               VARCHAR(20) NOT NULL DEFAULT 'demo',
    assessed_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- RETENTION POLICIES TABLE
-- =====================================================
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

-- =====================================================
-- WORKSPACE SETTINGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS workspace_settings (
    key         VARCHAR(50) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Idempotent column migrations for existing containers
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS data_mode VARCHAR(20) NOT NULL DEFAULT 'demo';
ALTER TABLE risk_assessments ADD COLUMN IF NOT EXISTS data_mode VARCHAR(20) NOT NULL DEFAULT 'demo';

-- =====================================================
-- INDEXES
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service_id);
CREATE INDEX IF NOT EXISTS idx_incidents_detected ON incidents(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_data_mode ON incidents(data_mode);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_service ON risk_assessments(service_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_assessed ON risk_assessments(assessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_data_mode ON risk_assessments(data_mode);
CREATE INDEX IF NOT EXISTS idx_service_deps_source ON service_dependencies(source_service_id);
CREATE INDEX IF NOT EXISTS idx_service_deps_target ON service_dependencies(target_service_id);
CREATE INDEX IF NOT EXISTS idx_incident_history_incident ON incident_history(incident_id);

-- =====================================================
-- SEED DATA: Default admin user
-- Password: admin123 (BCrypt hash)
-- =====================================================
INSERT INTO users (username, email, password_hash, full_name, role)
VALUES (
    'admin',
    'admin@synapse-riskops.local',
    '$2b$10$b213yKULfHN/8eiU1Z/Alu2jQZLblxFZWmIv.RdJ9ODKCgGYt6pdK',
    'System Administrator',
    'ADMIN'
) ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- =====================================================
-- SEED DATA: Sample services for dependency graph
-- =====================================================
INSERT INTO services (service_name, service_type, description, owner, criticality) VALUES
    ('api-gateway',       'GATEWAY',      'Main API gateway and load balancer',         'Platform Team',  'CRITICAL'),
    ('auth-service',      'MICROSERVICE', 'Authentication and authorization service',   'Security Team',  'CRITICAL'),
    ('user-service',      'MICROSERVICE', 'User management and profiles',               'Backend Team',   'HIGH'),
    ('order-service',     'MICROSERVICE', 'Order processing and management',            'Commerce Team',  'HIGH'),
    ('payment-service',   'MICROSERVICE', 'Payment processing and billing',             'Payments Team',  'CRITICAL'),
    ('inventory-service', 'MICROSERVICE', 'Inventory tracking and management',          'Supply Team',    'HIGH'),
    ('notification-svc',  'MICROSERVICE', 'Email, SMS, and push notifications',         'Platform Team',  'MEDIUM'),
    ('search-service',    'MICROSERVICE', 'Full-text search engine',                    'Search Team',    'MEDIUM'),
    ('cache-layer',       'INFRASTRUCTURE', 'Redis caching layer',                      'Platform Team',  'HIGH'),
    ('message-queue',     'INFRASTRUCTURE', 'RabbitMQ message broker',                  'Platform Team',  'CRITICAL'),
    ('postgres-primary',  'DATABASE',     'Primary PostgreSQL database',                'DBA Team',       'CRITICAL'),
    ('postgres-replica',  'DATABASE',     'Read replica PostgreSQL',                    'DBA Team',       'HIGH')
ON CONFLICT (service_name) DO NOTHING;

-- =====================================================
-- SEED DATA: Service dependencies
-- =====================================================
INSERT INTO service_dependencies (source_service_id, target_service_id, dependency_type)
SELECT s.id, t.id, dep.dep_type
FROM (VALUES
    ('api-gateway',       'auth-service',      'SYNC'),
    ('api-gateway',       'user-service',      'SYNC'),
    ('api-gateway',       'order-service',     'SYNC'),
    ('api-gateway',       'search-service',    'SYNC'),
    ('auth-service',      'postgres-primary',  'SYNC'),
    ('auth-service',      'cache-layer',       'SYNC'),
    ('user-service',      'postgres-primary',  'SYNC'),
    ('user-service',      'cache-layer',       'SYNC'),
    ('order-service',     'payment-service',   'SYNC'),
    ('order-service',     'inventory-service', 'SYNC'),
    ('order-service',     'postgres-primary',  'SYNC'),
    ('order-service',     'message-queue',     'ASYNC'),
    ('payment-service',   'postgres-primary',  'SYNC'),
    ('payment-service',   'message-queue',     'ASYNC'),
    ('inventory-service', 'postgres-primary',  'SYNC'),
    ('inventory-service', 'cache-layer',       'SYNC'),
    ('notification-svc',  'message-queue',     'ASYNC'),
    ('search-service',    'cache-layer',       'SYNC'),
    ('postgres-replica',  'postgres-primary',  'REPLICATION')
) AS dep(source_name, target_name, dep_type)
JOIN services s ON s.service_name = dep.source_name
JOIN services t ON t.service_name = dep.target_name
ON CONFLICT (source_service_id, target_service_id) DO NOTHING;

-- =====================================================
-- AUTONOMY POLICIES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS autonomy_policies (
    id                                      VARCHAR(50) PRIMARY KEY DEFAULT 'default',
    low_risk_auto_execute                  BOOLEAN NOT NULL DEFAULT TRUE,
    medium_risk_requires_approval           BOOLEAN NOT NULL DEFAULT TRUE,
    critical_services_always_require_approval BOOLEAN NOT NULL DEFAULT TRUE,
    min_historical_samples                  FLOAT NOT NULL DEFAULT 3.0,
    error_budget_threshold_percent          FLOAT NOT NULL DEFAULT 20.0,
    max_auto_recovery_time_seconds          FLOAT NOT NULL DEFAULT 60.0,
    updated_at                              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO autonomy_policies (id, low_risk_auto_execute, medium_risk_requires_approval, critical_services_always_require_approval, min_historical_samples, error_budget_threshold_percent, max_auto_recovery_time_seconds)
VALUES ('default', TRUE, TRUE, TRUE, 3.0, 20.0, 60.0)
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- REMEDIATION RECORDS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS remediation_records (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id                     UUID REFERENCES incidents(id) ON DELETE SET NULL,
    service_name                    VARCHAR(100) NOT NULL,
    action                          VARCHAR(100) NOT NULL,
    runbook_id                      VARCHAR(100),
    risk_level                      VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    autonomy_decision               VARCHAR(30) NOT NULL,
    approval_status                 VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    status                          VARCHAR(30) NOT NULL DEFAULT 'PROPOSED',
    approved_by                     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by_username            VARCHAR(100),
    approved_at                     TIMESTAMP WITH TIME ZONE,
    rejection_reason                TEXT,
    estimated_execution_seconds     FLOAT,
    estimated_recovery_seconds      FLOAT,
    estimate_source                 VARCHAR(30) NOT NULL DEFAULT 'calculated',
    estimate_uncertainty            VARCHAR(50),
    estimate_display                TEXT,
    actual_execution_seconds        FLOAT,
    actual_recovery_seconds         FLOAT,
    success                         BOOLEAN,
    post_remediation_health         VARCHAR(50),
    ansible_task_id                 VARCHAR(100),
    semaphore_url                   TEXT,
    execution_logs                  JSONB,
    pre_metrics                     JSONB,
    post_metrics                    JSONB,
    reasoning                       TEXT,
    evaluation_factors              JSONB,
    created_at                      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at                     TIMESTAMP WITH TIME ZONE,
    completed_at                    TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_remediation_records_service ON remediation_records(service_name);
CREATE INDEX IF NOT EXISTS idx_remediation_records_action ON remediation_records(action);
CREATE INDEX IF NOT EXISTS idx_remediation_records_incident ON remediation_records(incident_id);

-- =====================================================
-- AUTONOMY AUDIT LOGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS autonomy_audit_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    remediation_id      UUID REFERENCES remediation_records(id) ON DELETE CASCADE,
    event_type          VARCHAR(50) NOT NULL,
    service_name        VARCHAR(100) NOT NULL,
    action              VARCHAR(100) NOT NULL,
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    user_role           VARCHAR(50),
    user_username       VARCHAR(100),
    decision            VARCHAR(30),
    details             JSONB,
    timestamp           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_autonomy_audit_event ON autonomy_audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_autonomy_audit_timestamp ON autonomy_audit_logs(timestamp);

