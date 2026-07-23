"""Fetch private-module metadata from Terraform Cloud (HCP Terraform).

Reads:
    - Env var TFC_TOKEN : User/Team API token with read access to the private
                                                module registry.
    - Env var TFC_ORG   : Organization name (e.g. "JackTFOrg").
    - Optional TFC_HOST : Defaults to "app.terraform.io".

Writes:
    data/modules.json  -- normalized list consumed by generate_status_page.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

API_PAGE_SIZE = 50
REQUEST_TIMEOUT = 30
OUTPUT_PATH = Path("data/modules.json")

PROVIDER_COLORS = {
    "aws": "#f59e0b",
    "google": "#2563eb",
    "azurerm": "#0ea5e9",
    "azure": "#0ea5e9",
    "local": "#64748b",
    "random": "#8b5cf6",
    "time": "#0891b2",
}


def env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        print(f"ERROR: environment variable {name} is required", file=sys.stderr)
        sys.exit(1)
    return value or ""


def api_get(session: requests.Session, url: str) -> dict[str, Any]:
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    if resp.status_code == 401:
        raise SystemExit("ERROR: TFC token rejected (401). Check TFC_TOKEN secret.")
    resp.raise_for_status()
    return resp.json()


def list_modules(session: requests.Session, host: str, org: str) -> list[dict[str, Any]]:
    """Return all registry modules in the org across all pages."""
    modules: list[dict[str, Any]] = []
    url = (
        f"https://{host}/api/v2/organizations/{org}/registry-modules"
        f"?page%5Bsize%5D={API_PAGE_SIZE}"
    )
    while url:
        payload = api_get(session, url)
        modules.extend(payload.get("data", []))
        url = (payload.get("links") or {}).get("next")
    return modules


def module_detail(
    session: requests.Session,
    host: str,
    org: str,
    name: str,
    provider: str,
) -> dict[str, Any]:
    """Fetch the detail record for a single private module."""
    url = (
        f"https://{host}/api/v2/organizations/{org}"
        f"/registry-modules/private/{org}/{name}/{provider}"
    )
    return api_get(session, url)


def normalize(
    host: str,
    org: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Reduce a TFC module detail payload to just the fields the dashboard needs."""
    attrs = detail.get("data", {}).get("attributes", {}) or {}
    name = attrs.get("name")
    provider = attrs.get("provider")
    provider_id = (provider or "unknown").lower()

    versions = [
        v.get("version") for v in (attrs.get("version-statuses") or []) if v.get("version")
    ]
    latest = versions[0] if versions else None

    vcs = attrs.get("vcs-repo") or {}
    repo_identifier = vcs.get("identifier") or vcs.get("display-identifier")
    repo_url = f"https://github.com/{repo_identifier}" if repo_identifier else None

    # updated-at on the module reflects when the latest version was published.
    released_at = attrs.get("updated-at")

    registry_url = (
        f"https://{host}/app/{org}/registry/modules/private/{org}/{name}/{provider}"
        if name and provider
        else None
    )

    return {
        "name": name,
        "provider": provider,
        "namespace": attrs.get("namespace") or org,
        "status": attrs.get("status"),
        "latest_version": latest,
        "all_versions": versions,
        "released_at": released_at,
        "created_at": attrs.get("created-at"),
        "updated_at": attrs.get("updated-at"),
        "repo": repo_identifier,
        "repo_url": repo_url,
        "registry_source": (
            f"{host}/{org}/{name}/{provider}" if name and provider else None
        ),
        "registry_url": registry_url,
        "category": provider_id,
        "category_label": provider_id.upper() if provider_id == "aws" else provider_id.title(),
        "category_color": PROVIDER_COLORS.get(provider_id, "#64748b"),
        "changelog_url": "",
        "confluence_url": "",
    }


def build_category_index(
    modules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return the provider list actually in use (id, label, color, count)."""
    counts: dict[str, int] = {}
    for m in modules:
        counts[m["category"]] = counts.get(m["category"], 0) + 1

    result: list[dict[str, Any]] = []
    for cat_id, count in counts.items():
        result.append(
            {
                "id": cat_id,
                "label": cat_id.upper() if cat_id == "aws" else cat_id.title(),
                "color": PROVIDER_COLORS.get(cat_id, "#64748b"),
                "count": count,
            }
        )
    result.sort(key=lambda c: c["label"].lower())
    return result


def main() -> int:
    token = env("TFC_TOKEN")
    org = env("TFC_ORG")
    host = env("TFC_HOST", required=False, default="app.terraform.io")

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.api+json",
            "User-Agent": "module-release-dashboard/1.0",
        }
    )

    print(f"Fetching modules for org '{org}' from {host} ...")
    listing = list_modules(session, host, org)
    print(f"Found {len(listing)} module(s). Fetching details ...")

    modules: list[dict[str, Any]] = []
    for entry in listing:
        attrs = entry.get("attributes") or {}
        name = attrs.get("name")
        provider = attrs.get("provider")
        if not name or not provider:
            continue
        try:
            detail = module_detail(session, host, org, name, provider)
        except (requests.HTTPError, requests.exceptions.RequestException) as exc:
            print(f"WARN: skipping {name}/{provider}: {exc}", file=sys.stderr)
            continue
        modules.append(normalize(host, org, detail))

    modules.sort(key=lambda m: (m.get("name") or "").lower())

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "organization": org,
        "host": host,
        "module_count": len(modules),
        "categories": build_category_index(modules),
        "modules": modules,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(modules)} module(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
