# AI 资讯推送机器人

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 填写配置（main.py 顶部）
```python
ANTHROPIC_API_KEY = "sk-ant-..."   # Anthropic API Key
FEISHU_WEBHOOK    = "https://open.feishu.cn/open-apis/bot/v2/hook/..." # feishu bot webhook
```

### 3. 立即测试
```bash
python main.py --now
```

### 4. 定时运行（每天 9:00 自动推送）
```bash
python main.py

#后台运行
nohup python3 main.py > push.log 2>&1 &
```

### 5. 单个数据源测试
```bash
# RSS（默认）
python main.py --test https://openai.com/news/rss.xml

# 网页爬取
python main.py --test https://karpathy.ai --scrape
```
---

<!-- ## 生产部署方案（推荐）

### 方案A：Linux 服务器 + cron
```bash
# crontab -e 添加以下行（每天9点执行）
0 9 * * * /usr/bin/python3 /path/to/main.py --now >> /var/log/ai_newsletter.log 2>&1
```

### 方案B：Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
```

### 方案C：GitHub Actions（免费，每天定时触发）
在仓库创建 `.github/workflows/newsletter.yml`：
```yaml
name: AI Newsletter
on:
  schedule:
    - cron: '0 1 * * *'   # UTC 1:00 = 北京时间 9:00
  workflow_dispatch:        # 允许手动触发
jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python main.py --now
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```
> ⚠️ 注意：GitHub Actions 无持久化存储，SQLite去重在Actions环境中每次重置。  
> 建议将 DB 存到 artifacts 或改用 Redis/外部数据库。

---

## 配置说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `LOOKBACK_HOURS` | 12 | 抓取过去N小时的内容 |
| `PUSH_HOUR` | 9 | 定时推送小时 |
| `MAX_ITEMS_PER_SECTION` | 5 | 每板块展示最多N条 |

--- -->

## 内容板块对应

| 板块 | 信源类型 |
|------|---------|
| 🤖 模型更新 | OpenAI/Anthropic/DeepMind/xAI/Mistral博客、Qwen、Seed、Black Forest Labs等模型官方网站 |
| 🔬 研究前沿 | arXiv (cs.AI/LG/CV/GR)、OpenAI Research、Anthropic Research、Thinking Machines Lab |
| 💼 应用层追踪 | Higgsfield、Krea、Recraft、Fal、Pika、Suno、Meshy、Manus、Character.AI、Talkie等 |
| 📰 媒体 | 机器之心、量子位、TechCrunch、VentureBeat、Wired、GitHub Trending等 |
| 💰 一级市场 | YC Blog、a16z、Sequoia、Crunchbase、TechCrunch Venture |
| 📈 二级市场 | 实时股价表格（Google、Meta、NVIDIA、MSFT、Adobe），含估值/财务/指引 |
| 💡 高质量观点 | Karpathy、Lilian Weng、Simon Willison、Sam Altman、Lex Fridman、Dwarkesh等 |

---
<!-- 
## 扩展开发

### 添加新的RSS源
在 `RSS_SOURCES` 列表中添加：
```python
{"name": "新信源名", "url": "RSS地址", "lang": "zh/en", "category": "model/biz/funding/opinion"},
```

### 添加Twitter/X监控
需要 X API v2 访问权限，可用 `tweepy` 库监控指定账号的推文：
- @sama (Sam Altman)
- @karpathy
- @ylecun
- @GaryMarcus

### 添加财务数据（二级市场）
可集成 `yfinance` 库自动拉取股价：
```python
import yfinance as yf
tickers = ["GOOGL", "META", "NVDA", "MSFT", "ADBE"]
data = yf.download(tickers, period="1d")
```

---

## 费用估算

| 服务 | 费用 |
|------|------|
| Claude API（每天60条摘要） | ~$0.05/天 |
| 服务器（VPS最低配）| ~$5/月 |
| GitHub Actions | 免费（2000分钟/月）|

每月总费用约 **$6.5** 即可运行。 -->
