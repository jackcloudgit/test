"""Render data/modules.json into public/index.html using a Jinja2 template."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

DATA_PATH = Path("data/modules.json")
TEMPLATE_DIR = Path("templates")
TEMPLATE_NAME = "index.html.j2"
OUTPUT_DIR = Path("public")
OUTPUT_FILE = OUTPUT_DIR / "index.html"


def format_iso(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def main() -> int:
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found. Run fetch_module_versions.py first.", file=sys.stderr)
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["fmt_date"] = format_iso

    template = env.get_template(TEMPLATE_NAME)
    html = template.render(**data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    # Copy raw JSON alongside the HTML so it can also be consumed programmatically.
    shutil.copy2(DATA_PATH, OUTPUT_DIR / "modules.json")

    print(f"Wrote {OUTPUT_FILE} ({len(data.get('modules', []))} module(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
