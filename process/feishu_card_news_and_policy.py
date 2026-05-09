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
import anthropic
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


def _dedup_by_claude(items: list[dict], top_n: int = 5) -> list[dict]:
    """Use Claude to semantically deduplicate news items and return top_n unique events."""
    if len(items) <= 1:
        return items

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    n = len(items)
    numbered = "\n".join(
        f"{i+1}. {item['title']}" for i, item in enumerate(items)
    )
    prompt = (
        f"以下共 {n} 条新闻标题（编号 1-{n}），其中可能有多条报道同一事件。\n"
        "去重规则：只要涉及同一产品、同一公司行为、或同一事件，无论角度或侧重点不同，都视为重复，每组只保留信息最完整的一条。\n"
        "请输出去重后保留的所有编号，按原顺序排列，用逗号分隔。\n"
        f"只输出数字编号（1-{n} 之间），不要输出其他任何内容。\n\n"
        f"{numbered}"
    )

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    try:
        indices = [int(x.strip()) - 1 for x in raw.split(",") if x.strip().isdigit()]
        indices = [i for i in indices if 0 <= i < n]
    except Exception:
        indices = list(range(n))

    return [items[i] for i in indices][:top_n]


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
        # url dedup first, then sort by importance
        seen_urls: set[str] = set()
        unique = []
        for item in items:
            url = item.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            unique.append(item)
        sorted_items = sorted(unique, key=lambda x: x.get("importance", 0), reverse=True)
        deduped[key] = _dedup_by_claude(sorted_items)
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
