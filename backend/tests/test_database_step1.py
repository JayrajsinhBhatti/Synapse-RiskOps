"""
Synapse RiskOps - Week 5 Step 1 Database Verification Test
==========================================================
Owner: Person 2 | Week: 5

Verifies:
1. Async connection to PostgreSQL via asyncpg
2. ORM models mapping to live tables created by docker/postgres/init.sql
3. Seed data verification: users (admin), services (12), dependencies (19)
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, async_engine
from app.models import User, Service, ServiceDependency, Incident


async def _async_test_database_connection():
    print("=" * 70)
    print("WEEK 5 - STEP 1: POSTGRESQL CONNECTION & ORM VERIFICATION")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        # 1. Test Users table & seed admin
        user_result = await session.execute(select(User))
        users = user_result.scalars().all()
        print(f"\n[1] Users in DB: {len(users)}")
        for u in users:
            print(f"    - User: {u.username} (role: {u.role}, email: {u.email})")
        assert len(users) >= 1, "Expected at least 1 user (admin) in DB"
        admin = next((u for u in users if u.username == "admin"), None)
        assert admin is not None, "Admin user not found"
        print("    --> Users table & ORM model: VERIFIED PASS")

        # 2. Test Services table & seed services
        service_result = await session.execute(select(Service))
        services = service_result.scalars().all()
        print(f"\n[2] Services in DB: {len(services)}")
        assert len(services) == 12, f"Expected 12 services in DB, found {len(services)}"
        print(f"    - Sample services: {[s.service_name for s in services[:4]]}...")
        print("    --> Services table & ORM model: VERIFIED PASS")

        # 3. Test Service Dependencies table
        dep_result = await session.execute(select(ServiceDependency))
        deps = dep_result.scalars().all()
        print(f"\n[3] Service Dependencies in DB: {len(deps)}")
        assert len(deps) == 19, f"Expected 19 dependencies in DB, found {len(deps)}"
        print("    --> Service dependencies table & ORM model: VERIFIED PASS")

        # 4. Test Incidents table structure query
        inc_result = await session.execute(select(Incident).limit(5))
        incidents = inc_result.scalars().all()
        print(f"\n[4] Incidents in DB: {len(incidents)} (empty initially)")
        print("    --> Incidents table & ORM model: VERIFIED PASS")

    print("\n" + "=" * 70)
    print("ALL STEP 1 DATABASE VERIFICATIONS PASSED!")
    print("=" * 70)


def test_database_connection_step1():
    asyncio.run(_async_test_database_connection())


if __name__ == "__main__":
    test_database_connection_step1()
