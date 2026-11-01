"""Simple local login with two roles: submitter and reviewer.
HTTP Basic Auth, credentials configured via .env with local-dev defaults
(explicitly documented as demo-only, never for a real deployment).
"""
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

# Local-dev defaults so the app runs without any .env setup. Override via
# .env for anything beyond a solo local demo.
DEFAULT_CREDENTIALS = {
    "submitter": ("submitter", "submitter123"),
    "reviewer": ("reviewer", "reviewer123"),
}


def _role_credentials(role: str) -> tuple[str, str]:
    default_username, default_password = DEFAULT_CREDENTIALS[role]
    username = os.environ.get(f"{role.upper()}_USERNAME", default_username)
    password = os.environ.get(f"{role.upper()}_PASSWORD", default_password)
    return username, password


class Identity:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role


def get_current_identity(credentials: HTTPBasicCredentials = Depends(security)) -> Identity:
    for role in ("submitter", "reviewer"):
        username, password = _role_credentials(role)
        username_ok = secrets.compare_digest(credentials.username, username)
        password_ok = secrets.compare_digest(credentials.password, password)
        if username_ok and password_ok:
            return Identity(username=credentials.username, role=role)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def require_reviewer(identity: Identity = Depends(get_current_identity)) -> Identity:
    if identity.role != "reviewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="reviewer role required")
    return identity
