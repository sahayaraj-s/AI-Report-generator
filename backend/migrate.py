"""
DB Migration: Add new columns to institutes table for editable units, departments, and scoring weights.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlalchemy
from app.database import engine, Base
from app.models import *  # noqa: import all models

# Create any new tables
Base.metadata.create_all(bind=engine)

# Add columns via ALTER TABLE (SQLite safe — ignores if already exists)
new_columns = [
    ("kauvery_units_json", "TEXT"),
    ("departments_json", "TEXT"),
    ("skill_weight_pct", "FLOAT DEFAULT 75.0"),
    ("attendance_weight_pct", "FLOAT DEFAULT 25.0"),
]

with engine.connect() as conn:
    for col_name, col_type in new_columns:
        try:
            conn.execute(sqlalchemy.text(
                f"ALTER TABLE institutes ADD COLUMN {col_name} {col_type}"
            ))
            conn.commit()
            print(f"  + Added column: institutes.{col_name}")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"  ~ Column already exists: institutes.{col_name}")
            else:
                print(f"  ! Error on {col_name}: {e}")

print("Migration complete.")
