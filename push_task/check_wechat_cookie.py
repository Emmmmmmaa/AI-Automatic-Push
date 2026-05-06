#!/usr/bin/env python3
"""
check_wechat_cookie.py — 检查微信公众号 cookie/token 是否过期
如果凭证失效，通过飞书 webhook 发送告警通知。

用法:
    python push_task/check_wechat_cookie.py
    # 或在 cron 中定期运行
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")


def _wechat_cookie() -> dict:
    return {
        "wxuin":       os.environ.get("WECHAT_WXUIN", ""),
        "uuid":        os.environ.get("WECHAT_UUID", ""),
        "bizuin":      os.environ.get("WECHAT_BIZUIN", ""),
        "cert":        os.environ.get("WECHAT_CERT", ""),
        "data_ticket": os.environ.get("WECHAT_DATA_TICKET", ""),
        "slave_sid":   os.environ.get("WECHAT_SLAVE_SID", ""),
        "slave_user":  "gh_33df2c086412",
    }


def _missing_env_vars() -> list[str]:
    required = ["WECHAT_TOKEN", "WECHAT_WXUIN", "WECHAT_UUID",
                "WECHAT_BIZUIN", "WECHAT_CERT", "WECHAT_DATA_TICKET", "WECHAT_SLAVE_SID"]
    return [k for k in required if not os.environ.get(k)]


def check_wechat_credentials() -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    is_valid=True means credentials are working.
    """
    missing = _missing_env_vars()
    if missing:
        return False, f"以下环境变量未配置: {', '.join(missing)}"

    token = os.environ.get("WECHAT_TOKEN", "")
    cookies = _wechat_cookie()

    # 用一个固定的公众号 biz 做探测请求，取 sources.py 里第一个账号
    try:
        from sources import WECHAT_ACCOUNTS
        if not WECHAT_ACCOUNTS:
            return False, "sources.py 中 WECHAT_ACCOUNTS 为空，无法探测"
        probe_biz = WECHAT_ACCOUNTS[0]["biz"]
        probe_name = WECHAT_ACCOUNTS[0]["name"]
    except Exception as e:
        return False, f"加载 WECHAT_ACCOUNTS 失败: {e}"

    try:
        resp = requests.get(
            "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
            params={
                "sub": "list", "search_field": "null", "begin": 0, "count": 1,
                "query": "", "fakeid": probe_biz, "type": "101_1",
                "free_publish_type": 1, "sub_action": "list_ex",
                "token": token, "lang": "zh_CN", "f": "json", "ajax": 1,
            },
            cookies=cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                "x-requested-with": "XMLHttpRequest",
                "Referer": "https://mp.weixin.qq.com/",
            },
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        return False, f"网络请求失败: {e}"

    try:
        data = resp.json()
    except Exception:
        return False, f"响应解析失败，HTTP {resp.status_code}，内容: {resp.text[:200]}"

    base_resp = data.get("base_resp", {})
    ret = base_resp.get("ret")

    if ret == 0:
        return True, f"凭证有效（探测账号: {probe_name}）"

    # 常见错误码含义
    error_hints = {
        -1:   "系统错误",
        200013: "频率限制，请稍后再试",
        200014: "token 已失效，请重新登录微信公众平台获取",
        200040: "cookie 已过期，请重新登录获取",
        200003: "非法请求，cookie/token 可能已失效",
    }
    hint = error_hints.get(ret, f"未知错误码 ret={ret}")
    return False, f"凭证失效 [{probe_name}]: {hint}（err_msg: {base_resp.get('err_msg', '')}）"


def send_feishu_alert(message: str) -> bool:
    if not FEISHU_WEBHOOK:
        log.error("FEISHU_WEBHOOK 未配置，无法发送告警")
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "⚠️ 微信公众号凭证告警"},
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**检测时间：** {now}\n\n"
                            f"**问题详情：** {message}\n\n"
                            f"**处理方式：**\n"
                            f"1. 登录 [微信公众平台](https://mp.weixin.qq.com)\n"
                            f"2. 打开浏览器开发者工具 → Network，找到任意请求\n"
                            f"3. 复制 Cookie 和 token 参数\n"
                            f"4. 更新 .env 中的 `WECHAT_TOKEN` 及 `WECHAT_*` 字段"
                        ),
                    },
                }
            ],
        },
    }
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload,
                             headers={"Content-Type": "application/json"}, timeout=10)
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            log.info("飞书告警发送成功")
            return True
        else:
            log.error(f"飞书告警发送失败: {result}")
            return False
    except Exception as e:
        log.error(f"飞书告警异常: {e}")
        return False


def main():
    log.info("开始检查微信公众号凭证...")
    is_valid, reason = check_wechat_credentials()

    if is_valid:
        log.info(f"✅ 凭证正常: {reason}")
    else:
        log.warning(f"❌ 凭证失效: {reason}")
        send_feishu_alert(reason)

    return is_valid


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
