"""
process/subscriber.py — 订阅者管理，读写飞书多维表格订阅表。

news 表:   ZaJGbWgnkaTzchsPwp2clTTlnKb / tblVrBesSSCzHvRr
market 表: ZaJGbWgnkaTzchsPwp2clTTlnKb / tblcbStAoZErkmbH
字段: open_id, name, subscribed_at, status (active/inactive)
"""

import requests
from datetime import datetime

try:
    from process.feishu_bitable import get_tenant_token
except ModuleNotFoundError:
    from feishu_bitable import get_tenant_token

APP_TOKEN = "ZaJGbWgnkaTzchsPwp2clTTlnKb"

_TABLE_IDS = {
    "news":   "tblVrBesSSCzHvRr",
    "market": "tblcbStAoZErkmbH",
}


def _base(sub_type: str) -> str:
    return f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{_TABLE_IDS[sub_type]}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {get_tenant_token()}"}


def _text_field(value) -> str:
    if isinstance(value, list) and value:
        return value[0].get("text", "")
    return value or ""


def _find_record(open_id: str, sub_type: str) -> str | None:
    resp = requests.post(
        f"{_base(sub_type)}/records/search",
        headers=_headers(),
        json={
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {"field_name": "open_id", "operator": "is", "value": [open_id]}
                ],
            },
            "page_size": 1,
        },
        timeout=15,
    )
    items = resp.json().get("data", {}).get("items", [])
    return items[0]["record_id"] if items else None


def subscribe(open_id: str, sub_type: str, name: str = "") -> None:
    """订阅指定类型（news / market），写入对应的表。"""
    record_id = _find_record(open_id, sub_type)
    now_ms = int(datetime.now().timestamp() * 1000)

    if record_id:
        requests.put(
            f"{_base(sub_type)}/records/{record_id}",
            headers=_headers(),
            json={"fields": {"status": "active", "subscribed_at": now_ms}},
            timeout=15,
        )
    else:
        fields = {
            "open_id":       open_id,
            "status":        "active",
            "subscribed_at": now_ms,
        }
        if name:
            fields["name"] = name
        requests.post(
            f"{_base(sub_type)}/records",
            headers=_headers(),
            json={"fields": fields},
            timeout=15,
        )


def unsubscribe(open_id: str, sub_type: str) -> None:
    """取消订阅：从对应表中删除该用户记录。"""
    record_id = _find_record(open_id, sub_type)
    if not record_id:
        return
    requests.delete(
        f"{_base(sub_type)}/records/{record_id}",
        headers=_headers(),
        timeout=15,
    )


def get_subscribers(sub_type: str) -> list[str]:
    """返回指定表中所有 status=active 的 open_id 列表。"""
    resp = requests.post(
        f"{_base(sub_type)}/records/search",
        headers=_headers(),
        json={
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {"field_name": "status", "operator": "is", "value": ["active"]}
                ],
            },
            "page_size": 500,
        },
        timeout=15,
    )
    items = resp.json().get("data", {}).get("items", [])
    return [
        _text_field(item["fields"].get("open_id"))
        for item in items
        if item["fields"].get("open_id")
    ]
