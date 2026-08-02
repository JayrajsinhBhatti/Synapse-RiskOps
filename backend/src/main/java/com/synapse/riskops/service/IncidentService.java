package com.synapse.riskops.service;

/**
 * IncidentService.java
 * Owner: Person 2 | Week: 5
 *
 * Business logic layer for incident lifecycle management (create, update status,
 * assign, resolve). Called by IncidentController, uses IncidentRepository for
 * persistence. Also responsible for calling the ML Engine (via WebClient,
 * app.ml-engine.url in application.properties) to fetch risk scores, and calling
 * the GenAI agent service for diagnosis/guidance once that integration is wired
 * (Week 5 joint integration task).
 */
public class IncidentService {
    // TODO Week 5: implement incident CRUD + orchestration logic
}
