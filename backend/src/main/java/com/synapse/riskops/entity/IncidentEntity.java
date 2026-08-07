package com.synapse.riskops.entity;

/**
 * IncidentEntity.java
 * Owner: Person 2 | Week: 5
 *
 * JPA entity mapping to the `incidents` table defined in docker/postgres/init.sql.
 * Mirrors the shape of shared/schemas/incident_record.schema.json where applicable
 * (risk_score, confidence, predicted_failure, detected_at, resolved_at, etc.).
 * Used by IncidentRepository and returned/consumed via IncidentController.
 */
public class IncidentEntity {
    // TODO Week 5: map fields to incidents table columns (id, title, description,
    // severity, status, service_id, risk_score, confidence, predicted_failure,
    // detected_at, resolved_at, assigned_to, created_by, created_at, updated_at)
}
