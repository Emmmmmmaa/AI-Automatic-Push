"""
Feishu Bitable (多维表格) integration.
Writes collected news items to a Bitable table after crawling.
"""

import os
import time
import logging
import requests
from datetime import datetime

log = logging.getLogger(__name__)

APP_TOKEN = "ZaJGbWgnkaTzchsPwp2clTTlnKb"
TABLE_ID  = "tblB5hwdtlejr1xg"

_token_cache: dict = {"token": None, "expires_at": 0}


def get_tenant_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

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
        raise RuntimeError(f"Failed to get Feishu token: {data}")

    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + data.get("expire", 7200) - 60
    return token


BATCH_SIZE = 500


def _batch_insert(token: str, records: list[dict]) -> int:
    if not records:
        return 0
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"records": [{"fields": r} for r in records]},
        timeout=30,
    )
    data = resp.json()
    if data.get("code") == 0:
        return len(records)
    log.warning(f"Bitable batch insert failed: {data}")
    return 0


def write_items_to_bitable(items: list[dict]) -> int:
    """Insert crawled items into Feishu Bitable. Returns number of successful inserts."""
    if not items:
        return 0

    try:
        token = get_tenant_token()
    except Exception as e:
        log.error(f"Bitable: cannot get token: {e}")
        return 0

    year = datetime.now().year
    records = []
    for item in items:
        pub_time_ms = None
        pub_time_str = item.get("pub_time", "")
        if pub_time_str and pub_time_str != "nan":
            try:
                dt = datetime.strptime(f"{year}-{pub_time_str}", "%Y-%m-%d %H:%M")
                pub_time_ms = int(dt.timestamp() * 1000)
            except Exception:
                pass

        records.append({
            "title":       item.get("title", ""),
            "url":         item.get("url", ""),
            "summary":     item.get("summary", ""),
            "source":      item.get("source", ""),
            "category":    item.get("category", ""),
            "pub_time":    pub_time_ms,
            "source_type": item.get("source_type", ""),
            "push_time":   int(datetime.now().timestamp() * 1000),
        })

    success = 0
    for i in range(0, len(records), BATCH_SIZE):
        success += _batch_insert(token, records[i:i + BATCH_SIZE])

    log.info(f"Bitable: wrote {success}/{len(items)} records")
    return success
