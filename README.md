# 🧠 Synapse RiskOps

**Autonomous AI-Powered Risk Operations Pipeline**

> *Predicting Failures Before They Happen, Diagnosing Root Causes Instantly, and Guiding Engineers to Recovery — Autonomously.*

---

## 📋 Overview

Synapse RiskOps is a production-grade risk operations platform that continuously ingests server logs and metrics, uses machine learning to predict failures before they occur, maps service dependencies to trace failure propagation, and generates real-time risk assessments for engineering teams.

### Key Capabilities (Person 2 — This Repository)

| Capability | Technology | Description |
|---|---|---|
| **Anomaly Detection** | Isolation Forest | Real-time anomaly scoring on streaming metrics |
| **Failure Prediction** | Prophet / Statsmodels | Time-series forecasting with predicted failure windows |
| **Dependency Mapping** | NetworkX | Graph-based service dependency modeling and traversal |
| **Risk Scoring** | Custom Pipeline | Composite risk scores with confidence intervals |
| **Incident Management** | Spring Boot | Full CRUD incident lifecycle with audit trails |
| **Authentication** | JWT + Spring Security | Secure API access with role-based authorization |
| **Dashboard** | React + Vite | Real-time risk visualization with interactive graphs |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌────────────────────┐     ┌──────────────┐
│   React          │────▶│  Spring Boot       │────▶│  PostgreSQL   │
│   Dashboard      │     │  Backend           │     │  Database     │
│   (Port 5173)    │     │  (Port 8080)       │     │  (Port 5432)  │
└─────────────────┘     └────────────────────┘     └──────────────┘
                               │
                               ▼
                        ┌────────────────────┐
                        │  FastAPI ML Engine  │
                        │  (Port 8000)        │
                        └────────────────────┘
```

---

## 📁 Project Structure

```
Synapse-RiskOps/
├── backend/                    # Spring Boot Backend
│   ├── src/main/java/com/synapse/riskops/
│   │   ├── config/             # Security, CORS, App config
│   │   ├── controller/         # REST API controllers
│   │   ├── dto/                # Data Transfer Objects
│   │   ├── entity/             # JPA entities
│   │   ├── exception/          # Custom exceptions
│   │   ├── repository/         # Data access layer
│   │   ├── security/           # JWT, auth filters
│   │   └── service/            # Business logic
│   ├── src/main/resources/     # Application properties
│   ├── Dockerfile
│   └── pom.xml
│
├── ml-engine/                  # FastAPI ML Engine
│   ├── app/
│   │   ├── api/                # API route handlers
│   │   ├── core/               # Config, dependencies
│   │   ├── models/             # ML model classes
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   └── main.py             # FastAPI app entry
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # React Dashboard
│   ├── src/
│   │   ├── api/                # Axios API client
│   │   ├── components/         # Reusable UI components
│   │   ├── context/            # React context providers
│   │   ├── hooks/              # Custom React hooks
│   │   ├── layouts/            # Page layouts
│   │   ├── pages/              # Route pages
│   │   └── utils/              # Helper utilities
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── docker/                     # Docker support files
│   └── postgres/
│       └── init.sql            # Database initialization
│
├── sample-data/                # Sample CSV data for testing
│   ├── sample_metrics.csv
│   ├── sample_logs.csv
│   └── sample_dependencies.csv
│
├── docs/                       # Documentation
│
├── .env.example                # Environment variable template
├── .gitignore
├── docker-compose.yml          # Multi-service orchestration
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- [Git](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Synapse-RiskOps
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values (defaults work for local dev)
```

### 3. Start All Services

```bash
docker compose up --build
```

### 4. Access the Application

| Service | URL |
|---|---|
| React Dashboard | http://localhost:5173 |
| Spring Boot API | http://localhost:8080 |
| API Documentation | http://localhost:8080/swagger-ui.html |
| FastAPI ML Engine | http://localhost:8000 |
| ML Engine Docs | http://localhost:8000/docs |

---

## 🔧 Development

### Run Services Individually

**ML Engine (Python)**
```bash
cd ml-engine
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend (Java)**
```bash
cd backend
./mvnw spring-boot:run
```

**Frontend (React)**
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS, React Flow, Recharts |
| Backend | Spring Boot 3.3, Spring Security, Spring Data JPA |
| ML Engine | FastAPI, Scikit-learn, Prophet, NetworkX |
| Database | PostgreSQL 16 |
| Auth | JWT (jjwt) |
| Deployment | Docker, Docker Compose |

---

## 👥 Team

| Member | Responsibilities |
|---|---|
| **Person 2** (This repo) | ML Engine, Backend, Frontend, Database, Docker, Deployment |
| **Person 1** | LangGraph, Gemini, Multi-agent AI, n8n, Root Cause LLM |

---

## 📄 License

This project is part of an academic capstone. All rights reserved.

---

## Full Monorepo Structure (Joint)

This repo now also includes Person 1's services, added alongside Person 2's
implementation above without changing anything already built:

```
synapse-riskops/
├── backend/          # Person 2 — Spring Boot (as described above)
├── ml-engine/         # Person 2 — FastAPI ML engine (as described above)
├── frontend/          # Person 2 — React dashboard (as described above)
├── docker/            # Person 2 — Postgres init scripts
├── sample-data/       # Person 2 — sample CSVs + Person 1's simulated_incidents/ (Week 3)
├── genai-agent/        # Person 1 — LangGraph + Gemini RCA agent, FastAPI
├── automation/         # Person 1 — n8n workflow exports
├── evaluation/         # Person 1 — metrics, backtesting, reports
├── shared/             # Joint — cross-service API contracts + incident schema
└── docs/               # Joint — architecture docs, diagrams, demo notes
```

Every placeholder file in `genai-agent/`, `automation/`, `evaluation/`, and the
not-yet-built parts of `backend/`, `ml-engine/`, and `frontend/` carries a header
comment stating its owner, target week, and what belongs there — see
`shared/api-contracts.md` for the endpoint contracts between services.
