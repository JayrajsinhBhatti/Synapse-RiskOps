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
    assessed_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service_id);
CREATE INDEX IF NOT EXISTS idx_incidents_detected ON incidents(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_service ON risk_assessments(service_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_assessed ON risk_assessments(assessed_at DESC);
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
    '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy',
    'System Administrator',
    'ADMIN'
) ON CONFLICT (username) DO NOTHING;

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
