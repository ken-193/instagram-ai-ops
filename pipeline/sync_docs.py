"""Mirror docs/ (and the idea database) into the Drive folders, updating files in place.

  python -m pipeline.sync_docs        (runs on push to main via .github/workflows/docs-sync.yml)
"""
from __future__ import annotations

from pathlib import Path

from . import drive

ROOT = Path(__file__).resolve().parents[1]
# Never write into 11_muse_queue here: Muse watches it and must only ever see approved reels.
MAP = [  # (repo path, Drive folder key, Drive file name)
    ("docs/00_README.md", "00_manual", "README.md"),
    ("docs/SYSTEM_DESIGN.md", "01_system", "SYSTEM_DESIGN.md"),
    ("docs/ENV_TEMPLATE.md", "01_system", "ENV_TEMPLATE.md"),
    ("docs/MUSE_HANDOFF.md", "01_system", "MUSE_HANDOFF.md"),
    ("ideas/IDEA_DATABASE.csv", "02_ideas", "IDEA_DATABASE.csv"),
    ("docs/SCRIPT_TEMPLATE.md", "04_scripts", "SCRIPT_TEMPLATE.md"),
    ("docs/APPROVAL_RULES.md", "06_pending", "APPROVAL_RULES.md"),
    ("docs/ANALYSIS_RULES.md", "08_reports", "ANALYSIS_RULES.md"),
    ("docs/BRAND_GUIDELINES.md", "09_templates", "BRAND_GUIDELINES.md"),
]


if __name__ == "__main__":
    for src, key, name in MAP:
        fid = drive.upload(ROOT / src, drive.FOLDERS[key], name)
        print(f"{src} -> {key}/{name} ({fid})")
