package com.synapse.riskops.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Health Check Controller
 * =======================
 * Provides a simple health endpoint for Docker health checks
 * and load balancer probes before Actuator is fully configured.
 */
@RestController
public class HealthController {

    @GetMapping("/api/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "healthy",
                "service", "synapse-riskops-backend",
                "version", "0.1.0"
        ));
    }
}
