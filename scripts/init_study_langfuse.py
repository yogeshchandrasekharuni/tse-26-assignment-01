"""Create private credentials for the separate local verification dashboard."""

import os
import secrets
import uuid

from housing.identity import ROOT

path = ROOT / "observability/langfuse/.env.study"
values = {
    "POSTGRES_PASSWORD": secrets.token_hex(24),
    "SALT": secrets.token_hex(32),
    "ENCRYPTION_KEY": secrets.token_hex(32),
    "NEXTAUTH_SECRET": secrets.token_hex(32),
    "CLICKHOUSE_PASSWORD": secrets.token_hex(24),
    "REDIS_PASSWORD": secrets.token_hex(24),
    "MINIO_PASSWORD": secrets.token_hex(24),
    "LANGFUSE_PUBLIC_KEY": f"pk-lf-{uuid.uuid4()}",
    "LANGFUSE_SECRET_KEY": f"sk-lf-{uuid.uuid4()}",
    "LANGFUSE_ADMIN_PASSWORD": secrets.token_urlsafe(24),
    "LANGFUSE_BASE_URL": "http://localhost:19310",
    "LANGFUSE_PROJECT_ID": "housing-trajectories",
}
path.parent.mkdir(parents=True, exist_ok=True)
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("Kept existing private study dashboard credentials.")
else:
    with os.fdopen(fd, "w") as stream:
        stream.write("# Local only. Never commit or include in evidence exports.\n")
        stream.writelines(f"{key}={value}\n" for key, value in values.items())
    print("Created private observability/langfuse/.env.study (mode 0600).")
print("Dashboard: http://localhost:19310; login: housing-review@example.invalid")
print("The local login password is LANGFUSE_ADMIN_PASSWORD in that ignored file.")
