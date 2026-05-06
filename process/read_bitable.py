"""
Debug script: read all records from Feishu Bitable table.
Requires env vars: FEISHU_APP_ID, FEISHU_APP_SECRET
"""

APP_TOKEN = "ZaJGbWgnkaTzchsPwp2clTTlnKb"
TABLE_ID  = "tblB5hwdtlejr1xg"
VIEW_ID   = "vewpytzyHG"


import os
import json
import requests
from pathlib import Path

# Load .env from the same directory as this script
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def get_tenant_token() -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={
            "app_id":     os.environ["FEISHU_APP_ID"],
            "app_secret": os.environ["FEISHU_APP_SECRET"],
        },
        timeout=10,
    )
    data = resp.json()
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"Failed to get token: {data}")
    return token


def read_all_records(token: str, view_id: str = VIEW_ID) -> list[dict]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
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

        items = data.get("data", {}).get("items", [])
        records.extend(items)

        has_more = data.get("data", {}).get("has_more", False)
        page_token = data.get("data", {}).get("page_token")
        if not has_more or not page_token:
            break

    return records


TEMPLATE_ID      = "AAqeZdm8euiyO"
TEMPLATE_VERSION = "1.0.1"

CATEGORY_MAP = {
    "model":         "model_updates",
    "research":      "research",
    "creative":      "app_tracking",
    "social":        "app_tracking",
    "biz":           "media",
    "tech":          "media",
    # "public_market": "public_market",
    "funding":       "funding",
    "opinion":       "opinions",
}


def wrap_card_payload(
    template_variable: dict,
    template_id: str = TEMPLATE_ID,
    template_version: str = TEMPLATE_VERSION,
) -> dict:
    """Wrap a template_variable dict into a full Feishu webhook card body."""
    return {
        "msg_type": "interactive",
        "card": {
            "type": "template",
            "data": {
                "template_id":           template_id,
                "template_version_name": template_version,
                "template_variable":     template_variable,
            },
        },
    }


def build_card_variables(token: str = None) -> dict:
    """Return grouped template variables from the AI news table (without wrapping)."""
    if token is None:
        token = get_tenant_token()
    records = read_all_records(token)
    grouped: dict[str, list] = {}
    seen_urls: set[str] = set()
    for rec in records:
        fields = rec.get("fields", {})
        url = fields.get("url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        category = fields.get("category", "unknown")
        variable_key = category
        summary_raw = fields.get("summary-cn") or fields.get("summary", "")
        grouped.setdefault(variable_key, []).append({
            "title":      fields.get("title-cn") or fields.get("title", ""),
            "url":        url,
            "summary":    summary_raw[:500],
            "importance": int(fields["importance"]) if fields.get("importance") else 0,
            "source":     fields.get("source", ""),
        })
    return grouped


def build_card_payload(records: list[dict] = None, token: str = None) -> dict:
    """Build the full Feishu card payload from AI news table."""
    if records is None:
        grouped = build_card_variables(token)
    else:
        grouped = {}
        for rec in records:
            fields = rec.get("fields", {})
            category = fields.get("category", "unknown")
            variable_key = category
            summary_raw = fields.get("summary-cn") or fields.get("summary", "")
            grouped.setdefault(variable_key, []).append({
                "title":      fields.get("title-cn") or fields.get("title", ""),
                "url":        fields.get("url", ""),
                "summary":    summary_raw[:500],
                "importance": int(fields["importance"]) if fields.get("importance") else 0,
                "source":     fields.get("source", ""),
            })
    return wrap_card_payload(grouped)


def main():
    import sys
    as_json = "--json" in sys.argv

    token = get_tenant_token()
    records = read_all_records(token)
    payload = build_card_payload(records)

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        webhook = os.environ.get("FEISHU_WEBHOOK", "")
        if not webhook:
            print("FEISHU_WEBHOOK not set")
        else:
            resp = requests.post(webhook, json=payload, timeout=10)
            print(f"Push result: {resp.json()}")


if __name__ == "__main__":
    main()
