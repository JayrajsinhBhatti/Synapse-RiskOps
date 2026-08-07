# =====================================================
# Synapse RiskOps - Backend Dockerfile
# Multi-stage build for Spring Boot (Java 21)
# =====================================================

# ----- Stage 1: Build -----
FROM maven:3.9-eclipse-temurin-21-alpine AS build

WORKDIR /app

# Copy only POM first for dependency caching
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source and build
COPY src ./src
RUN mvn clean package -DskipTests -B

# ----- Stage 2: Runtime -----
FROM eclipse-temurin:21-jre-alpine AS runtime

WORKDIR /app

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built JAR from build stage
COPY --from=build /app/target/*.jar app.jar

# Expose Spring Boot port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

# JVM tuning for containers
ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
