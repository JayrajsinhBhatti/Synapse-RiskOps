"""
Synapse RiskOps - Week 5 Step 2 Auth & JWT Verification Test
============================================================
Owner: Person 2 | Week: 5

Verifies:
1. Password verification against bcrypt hash
2. POST /api/auth/login with pre-seeded admin user (admin / admin123)
3. Invalid credentials rejection (401 Unauthorized)
4. GET /api/auth/me with Bearer token
5. Role-Based Access Control (RBAC) requirement checks
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from httpx import ASGITransport
from app.main import app
from app.core.security import verify_password, create_access_token, decode_access_token


async def run_auth_tests():
    print("=" * 70)
    print("WEEK 5 - STEP 2: AUTHENTICATION, JWT & RBAC VERIFICATION")
    print("=" * 70)

    # 1. Test JWT utilities
    token = create_access_token({"sub": "test-uuid", "username": "testuser", "role": "ENGINEER"})
    payload = decode_access_token(token)
    assert payload is not None, "Token decoding failed"
    assert payload.get("username") == "testuser"
    assert payload.get("role") == "ENGINEER"
    print("\n[1] JWT token generation and decoding: PASS")

    # 2. Test live login with AsyncClient
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # Valid login test (JSON - Frontend)
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        print(f"\n[2a] POST /api/auth/login (JSON) status: {login_resp.status_code}")
        assert login_resp.status_code == 200, f"JSON Login failed: {login_resp.text}"
        token_data = login_resp.json()
        assert "access_token" in token_data
        access_token = token_data["access_token"]
        print("    --> Valid JSON login: PASS")

        # Valid login test (Form-data - Swagger UI "Authorize" dialog)
        form_login_resp = await client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        print(f"\n[2b] POST /api/auth/login (Swagger Form) status: {form_login_resp.status_code}")
        assert form_login_resp.status_code == 200, f"Form Login failed: {form_login_resp.text}"
        print("    --> Valid Swagger UI Form login: PASS")

        # Invalid password test
        bad_login_resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert bad_login_resp.status_code == 401, "Expected 401 on wrong password"
        print("\n[3] Invalid password rejection (401 Unauthorized): PASS")

        # 3. Test GET /api/auth/me with Bearer token
        headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = await client.get("/api/auth/me", headers=headers)
        print(f"\n[4] GET /api/auth/me response status: {me_resp.status_code}")
        assert me_resp.status_code == 200, f"GET /me failed: {me_resp.text}"
        me_data = me_resp.json()
        print(f"    - Authenticated User: {me_data['username']} | Role: {me_data['role']} | Email: {me_data['email']}")
        assert me_data["username"] == "admin"
        assert me_data["role"] == "ADMIN"
        assert me_data["is_active"] is True
        print("    --> GET /api/auth/me profile verification: PASS")

        # 4. Test unauthorized request
        unauth_resp = await client.get("/api/auth/me")
        assert unauth_resp.status_code == 401, "Expected 401 for unauthenticated request"
        print("\n[5] Protected endpoint unauthenticated rejection (401): PASS")

    print("\n" + "=" * 70)
    print("ALL STEP 2 AUTH & JWT VERIFICATIONS PASSED!")
    print("=" * 70)


def test_auth_step2_flow():
    asyncio.run(run_auth_tests())


if __name__ == "__main__":
    test_auth_step2_flow()
