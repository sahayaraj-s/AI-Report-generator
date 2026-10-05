"""
export_diagrams.py - Exports standalone high-res images of the system architecture,
data flow, and database ER diagrams for executive presentations and deliverables.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from generate_pdf_report import (
    generate_architecture_diagram,
    generate_dataflow_diagram,
    generate_er_diagram,
    ROOT_DIR
)

print("Exporting standalone diagrams...")

# 1. Architecture Diagram
arch_buf = generate_architecture_diagram()
arch_path = os.path.join(ROOT_DIR, "Architecture_Diagram.png")
with open(arch_path, "wb") as f:
    f.write(arch_buf.getvalue())
print(f"  [OK] Saved: {arch_path}")

# 2. Data Flow Diagram
df_buf = generate_dataflow_diagram()
df_path = os.path.join(ROOT_DIR, "Data_Flow_Diagram.png")
with open(df_path, "wb") as f:
    f.write(df_buf.getvalue())
print(f"  [OK] Saved: {df_path}")

# 3. Database ER Diagram
er_buf = generate_er_diagram()
er_path = os.path.join(ROOT_DIR, "Database_ER_Diagram.png")
with open(er_path, "wb") as f:
    f.write(er_buf.getvalue())
print(f"  [OK] Saved: {er_path}")

print("All diagrams exported successfully!")
