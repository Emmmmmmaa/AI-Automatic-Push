# AI 资讯推送机器人

自动采集 AI 资讯、政策新闻、二级市场行情，写入飞书多维表格，并通过飞书卡片模板定时推送。


## 推送流程

```
采集（push_task/）→ 写入飞书 Bitable → 读取（process/）→ 飞书卡片推送
```

每条内容经过关键词过滤和去重后落库，推送时通过飞书卡片模板渲染。

## 定时计划

| 脚本 | 内容 | 触发时间 |
|---|---|---|
| `push_task/push_news.py` | AI 资讯 | 每天 08:30 |
| `push_task/push_policy.py` | 政策新闻 | 每天 08:30 |
| `process/feishu_card_news_and_policy.py` | 早报卡片推送 | 每天 09:00 |
| `push_task/push_market.py` | 行业指数 + IR 新闻 + 个股新闻 | 每天 20:30 |
| `process/feishu_card_market.py` | 晚报卡片推送 | 每天 21:00 |

定时任务通过 macOS LaunchAgents 调度，日志写入 `logs/`。

```bash
# 查看状态
launchctl list | grep lovart

# 重新加载某个任务（以早报为例）
launchctl unload ~/Library/LaunchAgents/com.lovart.push-news.plist
launchctl load  ~/Library/LaunchAgents/com.lovart.push-news.plist
```

## 安装

```bash
pip install -r requirements.txt
```

配置 `.env`：

```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
ANTHROPIC_API_KEY=sk-ant-xxx
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

## 手动执行

```bash
# 采集 AI 资讯并写入 Bitable
python push_task/push_news.py

# 采集政策新闻并写入 Bitable
python push_task/push_policy.py

# 采集市场数据并写入 Bitable
python push_task/push_market.py

# 推送早报卡片（AI 资讯 + 政策）
python3 -m process.feishu_card_news_and_policy

# 推送晚报卡片（市场数据）
python3 process/feishu_card_market.py

# 打印卡片 payload（调试用，不实际推送）
python3 -m process.feishu_card_news_and_policy --json
python3 process/feishu_card_market.py --json
```

