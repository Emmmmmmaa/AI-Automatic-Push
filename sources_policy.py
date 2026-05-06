RSS_SOURCES = [
    # 权威官媒
    # {"name": "求是",             "url": "https://feedx.net/rss/qstheory.xml",          "lang": "zh", "category": "news"}, # 优先wechat
    {"name": "人民日报-政治",    "url": "http://www.people.com.cn/rss/politics.xml",    "lang": "zh", "category": "news"},
    {"name": "人民日报-经济",    "url": "http://www.people.com.cn/rss/finance.xml",     "lang": "zh", "category": "news"},
    # 深度研究
    {"name": "CF40研究",         "url": "https://cf40research.substack.com/feed",        "lang": "zh", "category": "deep"},
    {"name": "经济观察报",       "url": "https://rsshub.app/eeo/kuaixun",                "lang": "zh", "category": "deep"},
    # 商业媒体
    {"name": "钛媒体",           "url": "https://www.tmtpost.com/feed",                  "lang": "zh", "category": "media"},
    {"name": "澎湃新闻",         "url": "https://feedx.net/rss/thepaper.xml",            "lang": "zh", "category": "media"},
    {"name": "财新",             "url": "https://feedx.net/rss/caixin.xml",              "lang": "zh", "category": "media"},
    # 政府官方
    {"name": "国家统计局",       "url": "https://www.stats.gov.cn/wzgl/rss/",            "lang": "zh", "category": "gov"},
    
]

# 微信公众号（biz = fakeid，从公众号后台 URL 中获取）
WECHAT_ACCOUNTS = [
    {"name": "新华社",              "biz": "MzA4NDI3NjcyNA==",  "category": "news"},
    {"name": "人民日报",            "biz": "MjM5MjAxNDM4MA==",  "category": "news"},
    {"name": "求是",                "biz": "MjM5NjQ1NjY4MQ==",  "category": "news"},
    {"name": "学习时报",            "biz": "MzAwMjExNDU1Mw==",  "category": "news"},
    {"name": "南方周末",            "biz": "Njk5MTE1",           "category": "news"},
    {"name": "国家发改委",          "biz": "MzA3MDE5NjE2Mg==",  "category": "news"},
    {"name": "金融四十人论坛",      "biz": "MjM5NjgyNDk4NA==",  "category": "deep"},
    {"name": "首席经济学家论坛",    "biz": "MzYzMTM5MDA3MA==",  "category": "deep"},
    {"name": "财经五月花",          "biz": "MzkyMjY5MTQ1Nw==",  "category": "deep"},
    {"name": "国家金融与发展实验室", "biz": "MzA3NzEzMDc1MQ==", "category": "deep"},
    {"name": "经济学家圈",          "biz": "MzI0Mzk1NjIyMw==",  "category": "deep"},
]

# 网页抓取兜底（无 RSS）
SCRAPE_SOURCES = [
    # {"name": "学习时报",      "url": "https://www.studytimes.com.cn/sysyjx/syzqtg/", "category": "news"},
    # {"name": "金融四十人论坛", "url": "https://www.cf40.com/news_list.html",          "category": "deep"},
    {"name": "国务院政策",    "url": "https://www.gov.cn/zhengce/zuixin/",            "category": "gov"},
]


