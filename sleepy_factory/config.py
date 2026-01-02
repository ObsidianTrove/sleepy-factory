from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=REPO_ROOT / ".env")


class Settings(BaseModel):
    database_url: str


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value and value.strip():
        return value

    msg = (
        f"Missing required environment variable: {name}\n\n"
        "How to fix:\n"
        "1) Copy .env.example to .env\n"
        "2) Set DATABASE_URL in .env\n\n"
        "Example:\n"
        "DATABASE_URL=postgresql+psycopg://dev:dev@localhost:5432/sleepy\n\n"
        "If you are using Docker Compose for Postgres, make sure it is running:\n"
        "docker compose up -d\n"
    )
    raise RuntimeError(msg)


settings = Settings(database_url=_require_env("DATABASE_URL"))
