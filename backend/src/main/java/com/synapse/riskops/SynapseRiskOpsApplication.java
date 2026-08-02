package com.synapse.riskops;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Synapse RiskOps - Spring Boot Backend Entry Point
 * ==================================================
 * This is the main application class. Spring Boot auto-configures
 * everything based on the dependencies in pom.xml and the
 * properties in application.properties.
 *
 * Full implementation (controllers, services, entities) comes in Phase 8.
 */
@SpringBootApplication
public class SynapseRiskOpsApplication {

    public static void main(String[] args) {
        SpringApplication.run(SynapseRiskOpsApplication.class, args);
    }
}
