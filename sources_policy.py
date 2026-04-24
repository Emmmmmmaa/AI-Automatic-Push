RSS_SOURCES = [
    # 权威官媒
    {"name": "求是",             "url": "https://feedx.net/rss/qstheory.xml",          "lang": "zh", "category": "news"},
    {"name": "新华社",           "url": "http://rss.xinhuanet.com/rss/politics.xml",    "lang": "zh", "category": "news"},
    {"name": "人民日报-政治",    "url": "http://www.people.com.cn/rss/politics.xml",    "lang": "zh", "category": "news"},
    {"name": "人民日报-经济",    "url": "http://www.people.com.cn/rss/finance.xml",     "lang": "zh", "category": "news"},
    # 深度研究
    {"name": "首席经济学家论坛", "url": "https://rsshub.app/chinacef/portal/hot",       "lang": "zh", "category": "deep"},
    {"name": "CF40研究",         "url": "https://cf40research.substack.com/feed",        "lang": "zh", "category": "deep"},
    {"name": "经济观察报",       "url": "https://rsshub.app/eeo/kuaixun",                "lang": "zh", "category": "deep"},
    # 商业媒体
    {"name": "钛媒体",           "url": "https://www.tmtpost.com/feed",                  "lang": "zh", "category": "media"},
    {"name": "澎湃新闻",         "url": "https://feedx.net/rss/thepaper.xml",            "lang": "zh", "category": "media"},
    {"name": "财新",             "url": "https://feedx.net/rss/caixin.xml",              "lang": "zh", "category": "media"},
    {"name": "南方周末",         "url": "https://rsshub.app/infzm/2",                    "lang": "zh", "category": "media"},
    # 政府官方
    {"name": "国家统计局",       "url": "https://www.stats.gov.cn/wzgl/rss/",            "lang": "zh", "category": "gov"},
    {"name": "发改委",           "url": "https://www.ndrc.gov.cn/fzggw/jgsj/rss/",      "lang": "zh", "category": "gov"},
]

# 微信公众号（待接入）
# WECHAT_ACCOUNTS = [
#     # 已验证 __biz

#     # 待验证（biz 未确认）
#     {"name": "新华社",              "biz": ""},
#     {"name": "人民日报",            "biz": ""},
#     {"name": "求是",                "biz": ""},
    # {"name": "学习时报",            "biz": ""},
    # {"name": "金融四十人论坛",      "biz": ""},
#     {"name": "首席经济学家论坛",    "biz": ""},
    # {"name": "国家金融与发展实验室", "biz": ""},
    # {"name": "财经五月花",          "biz": ""},
    # {"name": "界面智库",            "biz": ""},
    # {"name": "经济学家圈",          "biz": ""},
# ]

# 网页抓取兜底（无 RSS）
SCRAPE_SOURCES = [
    {"name": "学习时报",      "url": "https://www.studytimes.com.cn/sysyjx/syzqtg/", "category": "news"},
    {"name": "金融四十人论坛", "url": "https://www.cf40.com/news_list.html",          "category": "deep"},
    {"name": "国务院政策",    "url": "https://www.gov.cn/zhengce/zuixin/",            "category": "gov"},
]
