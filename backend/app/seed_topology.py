"""
Seed/Update 10 Microservices Topology into PostgreSQL.
Populates `services` and `service_dependencies` tables so that the Synapse
React Flow Architecture Map and blast radius engines display the exact microservice graph.
"""

import asyncio
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.service import Service, ServiceDependency

SERVICES_DATA = [
    {"name": "api-gateway", "type": "GATEWAY", "criticality": "CRITICAL", "owner": "Platform Team", "desc": "Public API Gateway & edge router"},
    {"name": "auth-service", "type": "MICROSERVICE", "criticality": "CRITICAL", "owner": "Security Team", "desc": "User authentication & JWT issuance"},
    {"name": "user-service", "type": "MICROSERVICE", "criticality": "HIGH", "owner": "Backend Team", "desc": "User accounts & profile store"},
    {"name": "catalog-service", "type": "MICROSERVICE", "criticality": "HIGH", "owner": "Catalog Team", "desc": "Product catalog & inventory-enriched details"},
    {"name": "inventory-service", "type": "MICROSERVICE", "criticality": "HIGH", "owner": "Supply Team", "desc": "Warehouse stock levels & atomic reservation"},
    {"name": "cart-service", "type": "MICROSERVICE", "criticality": "HIGH", "owner": "Commerce Team", "desc": "User shopping carts & item calculation"},
    {"name": "order-service", "type": "MICROSERVICE", "criticality": "HIGH", "owner": "Commerce Team", "desc": "Distributed checkout & order lifecycle coordinator"},
    {"name": "payment-service", "type": "MICROSERVICE", "criticality": "CRITICAL", "owner": "Payments Team", "desc": "Payment gateway & financial authorization"},
    {"name": "notification-service", "type": "MICROSERVICE", "criticality": "MEDIUM", "owner": "Platform Team", "desc": "Order confirmation & customer alerts"},
    {"name": "recommendation-service", "type": "MICROSERVICE", "criticality": "MEDIUM", "owner": "Data Science Team", "desc": "AI product affinity & trending suggestions"},
]

DEPENDENCIES_DATA = [
    ("api-gateway", "auth-service", "SYNC"),
    ("api-gateway", "catalog-service", "SYNC"),
    ("api-gateway", "cart-service", "SYNC"),
    ("api-gateway", "order-service", "SYNC"),
    ("api-gateway", "recommendation-service", "SYNC"),
    ("auth-service", "user-service", "SYNC"),
    ("catalog-service", "inventory-service", "SYNC"),
    ("cart-service", "catalog-service", "SYNC"),
    ("order-service", "cart-service", "SYNC"),
    ("order-service", "inventory-service", "SYNC"),
    ("order-service", "payment-service", "SYNC"),
    ("order-service", "notification-service", "ASYNC"),
    ("recommendation-service", "catalog-service", "SYNC"),
]


async def seed_topology():
    print("[INFO] Seeding 10 Microservices and Dependencies into Synapse RiskOps...")
    async with AsyncSessionLocal() as session:
        # 1. Upsert Services
        service_map = {}
        for s in SERVICES_DATA:
            res = await session.execute(select(Service).where(Service.service_name == s["name"]))
            existing = res.scalar_one_or_none()
            if existing is None:
                new_svc = Service(
                    service_name=s["name"],
                    service_type=s["type"],
                    criticality=s["criticality"],
                    owner=s["owner"],
                    description=s["desc"],
                    is_active=True,
                )
                session.add(new_svc)
                await session.flush()
                service_map[s["name"]] = new_svc.id
                print(f"  + Added service: {s['name']}")
            else:
                existing.criticality = s["criticality"]
                existing.owner = s["owner"]
                existing.description = s["desc"]
                existing.is_active = True
                service_map[s["name"]] = existing.id
                print(f"  * Updated service: {s['name']}")

        # 2. Upsert Dependencies
        for src_name, tgt_name, dep_type in DEPENDENCIES_DATA:
            src_id = service_map.get(src_name)
            tgt_id = service_map.get(tgt_name)
            if not src_id or not tgt_id:
                continue

            dep_res = await session.execute(
                select(ServiceDependency).where(
                    ServiceDependency.source_service_id == src_id,
                    ServiceDependency.target_service_id == tgt_id,
                )
            )
            existing_dep = dep_res.scalar_one_or_none()
            if existing_dep is None:
                new_dep = ServiceDependency(
                    source_service_id=src_id,
                    target_service_id=tgt_id,
                    dependency_type=dep_type,
                )
                session.add(new_dep)
                print(f"  + Added edge: {src_name} --[{dep_type}]--> {tgt_name}")

        await session.commit()
        print("[SUCCESS] Topology successfully seeded in PostgreSQL!")


if __name__ == "__main__":
    asyncio.run(seed_topology())
