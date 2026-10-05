import os
import subprocess
import time
import shutil

DOCS_DIR = r"c:\Users\Lenovo\Downloads\ai-placement-dashboard-mvp\ai-placement-dashboard\docs\screenshots"
ARTIFACT_DIR = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\1feb78f7-9100-4896-af1f-f24d1bc814df\screenshots"

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

VIEWS = [
    ("dashboard", "http://localhost:5173/"),
    ("mini_chatbot", "http://localhost:5173/?chat=open"),
    ("skillbay_ai", "http://localhost:5173/ai"),
    ("upload", "http://localhost:5173/upload"),
]

VIEWPORTS = [
    ("1440", 1440, 900),
    ("768", 768, 1024),
    ("360", 360, 800),
]

for view_name, url in VIEWS:
    for vp_name, width, height in VIEWPORTS:
        fname = f"{view_name}_{vp_name}px.png"
        target_docs = os.path.join(DOCS_DIR, fname)
        target_art = os.path.join(ARTIFACT_DIR, fname)
        
        print(f"Capturing {fname} ({width}x{height}) from {url}...")
        args = [
            EDGE_PATH,
            "--headless=new",
            "--disable-gpu",
            f"--window-size={width},{height}",
            "--virtual-time-budget=2000",
            f"--screenshot={target_docs}",
            url
        ]
        res = subprocess.run(args, capture_output=True, text=True)
        if os.path.exists(target_docs):
            shutil.copy2(target_docs, target_art)
            print(f"  [OK] Saved: {fname} ({os.path.getsize(target_docs)} bytes)")
        else:
            print(f"  [FAIL] Could not capture {fname}: {res.stderr}")

print("Screenshot capture complete!")
