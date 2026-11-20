"""Login, registration, logout and protected routes."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_protected_routes_require_login(client):
    from app.main import app
    anon = TestClient(app)
    for path in ("/dashboard", "/analysis/history", "/metrics", "/model-info"):
        assert anon.get(path).status_code == 401, path
    assert anon.get("/health").status_code == 200


def test_register_login_logout_flow(client):
    from app.main import app
    c = TestClient(app)
    assert c.post("/auth/register", json={"name": "A", "email": "a@example.org", "password": "x"}).status_code == 422
    assert c.post("/auth/register", json={"name": "Alice Smith", "email": "alice@example.org", "password": "weakpass"}).status_code == 422
    r = c.post("/auth/register", json={"name": "Alice Smith", "email": "Alice@example.org", "password": "Password123"})
    assert r.status_code == 201 and "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/auth/me").json()["email"] == "alice@example.org"
    assert c.post("/auth/register", json={"name": "Alice", "email": "alice@example.org", "password": "Password123"}).status_code == 409
    assert c.post("/auth/logout").status_code == 204
    c.cookies.clear()
    assert c.get("/auth/me").status_code == 401
    assert c.post("/auth/login", json={"email": "alice@example.org", "password": "wrong-pass1"}).status_code == 401
    assert c.post("/auth/login", json={"email": "alice@example.org", "password": "Password123"}).status_code == 200
    assert c.get("/dashboard").status_code == 200


def test_password_is_hashed(client):
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import User
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == "tester@example.org"))
        assert u.password_hash.startswith("$2") and "Password123" not in u.password_hash


def test_remember_me_controls_cookie_lifetime(client):
    from app.main import app
    c = TestClient(app)
    c.post("/auth/register", json={"name": "Bob Jones", "email": "bob@example.org", "password": "Password123"})
    keep = c.post("/auth/login", json={"email": "bob@example.org", "password": "Password123", "remember": True})
    assert "max-age" in keep.headers["set-cookie"].lower()
    once = c.post("/auth/login", json={"email": "bob@example.org", "password": "Password123", "remember": False})
    assert once.status_code == 200 and "max-age" not in once.headers["set-cookie"].lower()
