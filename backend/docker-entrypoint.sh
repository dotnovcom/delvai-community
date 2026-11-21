#!/bin/sh
set -e

# Docker 卷挂载 /app/uploads 后常为 root，需在降权前修正属主
mkdir -p /app/uploads/admin /app/uploads/avatars /app/uploads/chat /app/uploads/files /app/uploads/signed
if [ "$(id -u)" = "0" ] && id appuser >/dev/null 2>&1; then
  chown -R appuser:appuser /app/uploads
fi

echo "[entrypoint] Waiting for PostgreSQL..."
python << 'PYEOF'
import os, sys, time
from urllib.parse import unquote, urlparse

import psycopg2

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit(1)
parsed = urlparse(url)
for _ in range(60):
    try:
        psycopg2.connect(
            host=parsed.hostname or "db",
            port=parsed.port or 5432,
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            dbname=(parsed.path or "/").lstrip("/") or "postgres",
        )
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
PYEOF

if [ -f /app/alembic/versions/028_legal_cache_log_sample_hits.py ]; then
  echo "[entrypoint] FATAL: 镜像内仍有冲突文件 alembic/versions/028_legal_cache_log_sample_hits.py"
  echo "[entrypoint] 请在宿主机删除该文件后执行: docker compose build --no-cache backend"
  exit 1
fi

head_count=$(alembic heads 2>/dev/null | grep -c '(head)' || true)
if [ "$head_count" -ne 1 ]; then
  echo "[entrypoint] FATAL: Alembic 迁移链异常（多个 head 或 revision 028 重复）"
  alembic heads 2>&1 || true
  echo "[entrypoint] 请执行: bash scripts/fix-alembic-baota.sh"
  exit 1
fi

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting: $*"
if [ "$(id -u)" = "0" ] && command -v gosu >/dev/null 2>&1 && id appuser >/dev/null 2>&1; then
  exec gosu appuser "$@"
fi
exec "$@"
