"""
process/policy.py — Merge AI news (read_bitable) + policy news into one card payload and push.

AI news table   : tblB5hwdtlejr1xg / vewpytzyHG  (via read_bitable.py)
Policy news table: tblW0ZKtC5yAeVFC / vewpytzyHG
"""

APP_TOKEN        = "ZaJGbWgnkaTzchsPwp2clTTlnKb"
TABLE_POLICY     = "tblW0ZKtC5yAeVFC"
VIEW_POLICY      = "vewpytzyHG"
TEMPLATE_ID      = "AAqeZdm8euiyO"
TEMPLATE_VERSION = "1.0.8"

import os
import sys
import json
import requests
from pathlib import Path
try:
    from process.read_bitable import (
        get_tenant_token, build_card_variables,
        wrap_card_payload, CATEGORY_MAP,
    )
except ModuleNotFoundError:
    from read_bitable import (
        get_tenant_token, build_card_variables,
        wrap_card_payload, CATEGORY_MAP,
    )

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())




def _read_records(token: str, table_id: str, view_id: str) -> list[dict]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    page_token = None
    while True:
        params = {"page_size": 100, "view_id": view_id}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error: {data}")
        records.extend(data.get("data", {}).get("items", []))
        if not data.get("data", {}).get("has_more") or not data.get("data", {}).get("page_token"):
            break
        page_token = data["data"]["page_token"]
    return records


def _group_records(records: list[dict], use_category_map: bool = False) -> dict:
    grouped: dict[str, list] = {}
    for rec in records:
        f = rec.get("fields", {})
        category = f.get("category", "unknown")
        key = CATEGORY_MAP.get(category, category) if use_category_map else category
        grouped.setdefault(key, []).append({
            "title":      f.get("title-cn") or f.get("title", ""),
            "url":        f.get("url", ""),
            "summary":    f.get("summary-cn") or f.get("summary", ""),
            "importance": int(f["importance"]) if f.get("importance") else 0,
            "source":     f.get("source", ""),
        })
    return grouped


def build_combined_variables(token: str = None) -> dict:
    """Merge AI news + policy news into one template_variable dict."""
    if token is None:
        token = get_tenant_token()

    ai_vars     = build_card_variables(token)
    policy_vars = _group_records(_read_records(token, TABLE_POLICY, VIEW_POLICY))

    merged = {**ai_vars}
    for key, items in policy_vars.items():
        merged.setdefault(key, []).extend(items)

    deduped = {}
    for key, items in merged.items():
        seen_urls = set()
        unique = []
        for item in items:
            url = item.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            unique.append(item)
        deduped[key] = sorted(unique, key=lambda x: x.get("importance", 0), reverse=True)[:5]
    return deduped


def build_combined_payload(token: str = None) -> dict:
    return wrap_card_payload(build_combined_variables(token), TEMPLATE_ID, TEMPLATE_VERSION)


if __name__ == "__main__":
    as_json = "--json" in sys.argv
    payload = build_combined_payload()

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        webhook = os.environ.get("FEISHU_WEBHOOK", "")
        if not webhook:
            print("FEISHU_WEBHOOK not set")
        else:
            resp = requests.post(webhook, json=payload, timeout=10)
            print(f"Push result: {resp.json()}")
