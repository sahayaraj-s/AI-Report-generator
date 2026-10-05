"""
copy_sqlite_to_postgres.py — Utility script to migrate data from local SQLite to PostgreSQL.

Usage:
    cd backend
    venv\\Scripts\\python.exe copy_sqlite_to_postgres.py --sqlite placement.db --pg "postgresql://user:pass@ep-xyz.neon.tech/neondb"
    # Or rely on DATABASE_URL from .env / environment

Note:
    - Never prints or logs confidential student names, emails, or scores.
    - Preserves primary keys and foreign keys.
    - Synchronizes PostgreSQL primary key sequences after migration.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker

from app.database import Base
# Import all models to register with Base.metadata
from app.models import (
    Institute, Course, Batch, Skill, Student,
    StudentScore, AnalysisResult, Upload, ActivityLog,
    JobRoleModel, AIChatSession, AIChatMessage
)

TABLES_IN_ORDER = [
    "institutes",
    "courses",
    "batches",
    "skills",
    "students",
    "student_scores",
    "analysis_results",
    "uploads",
    "activity_logs",
    "job_roles",
    "ai_chat_sessions",
    "ai_chat_messages",
]


def normalize_pg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def migrate(sqlite_path: str, pg_url: str):
    sqlite_file = Path(sqlite_path).resolve()
    if not sqlite_file.is_file():
        print(f"Error: Source SQLite file does not exist: {sqlite_file}")
        sys.exit(1)

    norm_pg_url = normalize_pg_url(pg_url)
    print(f"Connecting to source SQLite: {sqlite_file.name}")
    print("Connecting to target PostgreSQL database...")

    sqlite_engine = create_engine(f"sqlite:///{sqlite_file.as_posix()}", connect_args={"check_same_thread": False})
    pg_engine = create_engine(norm_pg_url, pool_pre_ping=True)

    # 1. Create all tables on target Postgres if not existing
    print("Ensuring target schema exists on PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)

    # 2. Copy data table by table in dependency order
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    total_records = 0

    with sqlite_engine.connect() as src_conn, pg_engine.connect() as dst_conn:
        for tbl_name in TABLES_IN_ORDER:
            if tbl_name not in sqlite_meta.tables or tbl_name not in pg_meta.tables:
                continue

            src_table = sqlite_meta.tables[tbl_name]
            dst_table = pg_meta.tables[tbl_name]

            # Read source rows
            rows = src_conn.execute(src_table.select()).mappings().all()
            if not rows:
                print(f"  • {tbl_name:20s}: 0 rows (skipped)")
                continue

            # Check existing count on destination to avoid duplicates
            existing_count = dst_conn.execute(text(f"SELECT COUNT(*) FROM {tbl_name}")).scalar()
            if existing_count > 0:
                print(f"  • {tbl_name:20s}: destination already has {existing_count} rows. Skipping to avoid conflict.")
                continue

            # Insert into destination
            dst_conn.execute(dst_table.insert(), [dict(r) for r in rows])
            dst_conn.commit()
            total_records += len(rows)
            print(f"  ✓ {tbl_name:20s}: copied {len(rows)} records")

            # Update PostgreSQL sequence if table has serial id
            try:
                dst_conn.execute(text(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{tbl_name}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {tbl_name}), 1),
                        (SELECT MAX(id) FROM {tbl_name}) IS NOT NULL
                    )
                """))
                dst_conn.commit()
            except Exception:
                # Some tables may not use serial id or driver may not support
                pass

    print(f"\nMigration completed successfully! Total records migrated: {total_records}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy SQLite database data to PostgreSQL")
    default_sqlite = Path(__file__).resolve().parent / "placement.db"
    parser.add_argument(
        "--sqlite",
        default=str(default_sqlite),
        help=f"Path to source SQLite .db file (default: {default_sqlite})"
    )
    parser.add_argument(
        "--pg",
        default=os.getenv("DATABASE_URL", ""),
        help="PostgreSQL connection string (default: reads DATABASE_URL from environment)"
    )

    args = parser.parse_args()
    if not args.pg:
        print("Error: PostgreSQL URL must be provided via --pg or DATABASE_URL environment variable.")
        sys.exit(1)

    migrate(args.sqlite, args.pg)
