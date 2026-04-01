RSS_SOURCES = [
    # [media] 中文技术媒体
    {"name": "机器之心",   "url": "https://www.jiqizhixin.com/rss",          "lang": "zh", "category": "tech"},
    {"name": "量子位",     "url": "https://www.qbitai.com/feed",              "lang": "zh", "category": "tech"},
    {"name": "新智元",     "url": "https://www.xinzhi.com/rss",               "lang": "zh", "category": "tech"},
    {"name": "36氪",       "url": "https://36kr.com/feed",                    "lang": "zh", "category": "biz"},
    {"name": "钛媒体",     "url": "https://www.tmtpost.com/feed",             "lang": "zh", "category": "biz"},

    # [tech] GitHub Trending（第三方 RSS）- 这个会输出太多
    # {"name": "GitHub Trending All",        "url": "https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml",        "lang": "en", "category": "model"},
    # {"name": "GitHub Trending Python",     "url": "https://mshibanami.github.io/GitHubTrendingRSS/daily/python.xml",     "lang": "en", "category": "model"},
    # {"name": "GitHub Trending TypeScript", "url": "https://mshibanami.github.io/GitHubTrendingRSS/daily/typescript.xml", "lang": "en", "category": "model"},

    # [tech] 教育
    {"name": "fast.ai",               "url": "https://www.fast.ai/index.xml",        "lang": "en", "category": "tech"},
    {"name": "Towards Data Science",  "url": "https://towardsdatascience.com/feed",  "lang": "en", "category": "tech"},

    # [media] 英文技术媒体
    {"name": "TechCrunch",         "url": "https://techcrunch.com/feed/",                              "lang": "en", "category": "biz"},
    {"name": "TechCrunch Venture", "url": "https://techcrunch.com/category/venture/feed/",             "lang": "en", "category": "funding"},
    {"name": "VentureBeat",        "url": "https://venturebeat.com/feed/",                             "lang": "en", "category": "tech"},
    {"name": "Wired AI",           "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss","lang": "en", "category": "tech"},
    {"name": "Ars Technica AI",    "url": "https://feeds.arstechnica.com/arstechnica/index",           "lang": "en", "category": "tech"},
    {"name": "The Information",    "url": "https://www.theinformation.com/feed",                       "lang": "en", "category": "biz"},
    {"name": "Inc.com",            "url": "https://www.inc.com/rss",                                   "lang": "en", "category": "biz"},
    {"name": "Entrepreneur",       "url": "https://www.entrepreneur.com/latest.rss",                   "lang": "en", "category": "biz"},
    {"name": "Fortune",            "url": "https://fortune.com/feed/",                                 "lang": "en", "category": "biz"},

    # [model] 模型更新：AI公司官方博客
    {"name": "OpenAI Blog",      "url": "https://openai.com/news/rss.xml",        "lang": "en", "category": "model"},
    {"name": "Google DeepMind",  "url": "https://deepmind.google/blog/rss.xml",   "lang": "en", "category": "model"},
    {"name": "Anthropic Blog",   "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "lang": "en", "category": "model"},
    {"name": "Microsoft AI",     "url": "https://blogs.microsoft.com/ai/feed/",   "lang": "en", "category": "model"},
    {"name": "Hugging Face",     "url": "https://huggingface.co/blog/feed.xml",   "lang": "en", "category": "model"},
    {"name": "Google AI Blog",   "url": "https://blog.google/technology/ai/rss/", "lang": "en", "category": "model"},
    {"name": "Meta AI Blog",     "url": "https://ai.meta.com/blog/rss/",          "lang": "en", "category": "model"},
    {"name": "xAI Blog",         "url": "https://x.ai/blog/rss.xml",              "lang": "en", "category": "model"},
    {"name": "Mistral Blog",     "url": "https://mistral.ai/news/rss",            "lang": "en", "category": "model"},

    # [research] arXiv（AI子领域）
    {"name": "arXiv cs.AI",   "url": "https://rss.arxiv.org/rss/cs.AI",      "lang": "en", "category": "research"},
    {"name": "arXiv cs.LG",   "url": "https://rss.arxiv.org/rss/cs.LG",      "lang": "en", "category": "research"},
    {"name": "arXiv cs.CV",   "url": "https://rss.arxiv.org/rss/cs.CV",      "lang": "en", "category": "research"},
    {"name": "arXiv cs.GR",   "url": "https://rss.arxiv.org/rss/cs.GR",      "lang": "en", "category": "research"},  # 图形学/3D生成

    # [research] 国际顶会博客（CVPR、ICCV、ACL 无 RSS） - 但是一般是call for paper这种
    # {"name": "NeurIPS Blog",  "url": "https://blog.neurips.cc/feed/",         "lang": "en", "category": "research"},
    # {"name": "ICML Blog",     "url": "https://blog.icml.cc/feed/",            "lang": "en", "category": "research"},
    # {"name": "ICLR Blog",     "url": "https://blog.iclr.cc/feed/",            "lang": "en", "category": "research"},
    # {"name": "AAAI Blog",     "url": "https://blog.aaai.org/feed/",           "lang": "en", "category": "research"},
    
    # [research] 研究机构 - RSS较少，先放几个代表性的，后续可以补充
    {"name": "OpenAI Research",        "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_openai_research.xml",      "lang": "en", "category": "research"},
    {"name": "Anthropic Research",     "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",   "lang": "en", "category": "research"},
    {"name": "Thinking Machines Lab",  "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_thinkingmachines.xml",     "lang": "en", "category": "research"},

    # [funding] 创投（一级市场）
    {"name": "YC Blog",        "url": "https://www.ycombinator.com/blog/rss",    "lang": "en", "category": "funding"},
    {"name": "a16z Blog",      "url": "https://a16z.com/feed/",                  "lang": "en", "category": "funding"},
    {"name": "Sequoia Blog",   "url": "https://www.sequoiacap.com/blog/rss.xml", "lang": "en", "category": "funding"},
    {"name": "Crunchbase News","url": "https://news.crunchbase.com/feed/",       "lang": "en", "category": "funding"},

    # [public_market] 二级市场财经
    {"name": "Reuters Tech",    "url": "https://feeds.reuters.com/reuters/technologyNews",                   "lang": "en", "category": "public_market"},
    {"name": "Bloomberg Tech",  "url": "https://feeds.bloomberg.com/technology/news.rss",                   "lang": "en", "category": "public_market"},
    {"name": "Seeking Alpha AI","url": "https://seekingalpha.com/tag/artificial-intelligence.xml",          "lang": "en", "category": "public_market"},

    # [creative] 创意设计工具官方博客
    {"name": "Adobe Blog",     "url": "https://blog.adobe.com/en/feed",         "lang": "en", "category": "creative"},
    {"name": "Figma Blog",     "url": "https://www.figma.com/blog/rss/",         "lang": "en", "category": "creative"},
    {"name": "Canva Newsroom", "url": "https://www.canva.com/newsroom/rss.xml",  "lang": "en", "category": "creative"},
    {"name": "Midjourney Blog","url": "https://midjourney.com/blog/rss",         "lang": "en", "category": "creative"},
    {"name": "Runway Blog",    "url": "https://runwayml.com/blog/rss",           "lang": "en", "category": "creative"},
    {"name": "Luma AI Blog",   "url": "https://lumalabs.ai/blog/rss",            "lang": "en", "category": "creative"},
    {"name": "Stability AI",   "url": "https://stability.ai/blog?format=rss",   "lang": "en", "category": "creative"},
    {"name": "Crepal",         "url": "https://crepal.ai/blog/feed/",            "lang": "en", "category": "creative"},

    # [opinion] 核心人物博客
    {"name": "Simon Willison",   "url": "https://simonwillison.net/atom/entries/",   "lang": "en", "category": "opinion"},
    {"name": "Lilian Weng",      "url": "https://lilianweng.github.io/index.xml",    "lang": "en", "category": "opinion"},
    {"name": "Greg Brockman",    "url": "https://blog.gregbrockman.com/feed",         "lang": "en", "category": "opinion"},
    {"name": "Wojciech Zaremba", "url": "https://medium.com/@woj.zaremba/feed",       "lang": "en", "category": "opinion"},
    {"name": "Stefan Pieterse",  "url": "https://steipete.me/rss.xml",                "lang": "en", "category": "opinion"},
    {"name": "Sam Altman Blog",  "url": "http://blog.samaltman.com/posts.atom",        "lang": "en", "category": "opinion"},
    {"name": "HN Buzzing",       "url": "https://hn.buzzing.cc/feed.xml",             "lang": "zh", "category": "opinion"},
    {"name": "AI Hub Today",     "url": "https://ai.hubtoday.app/blog/index.xml",     "lang": "zh", "category": "opinion"},

    # [opinion] 播客
    {"name": "Lex Fridman Podcast",  "url": "https://lexfridman.com/feed/podcast/",      "lang": "en", "category": "opinion"},
    {"name": "Dwarkesh Podcast",     "url": "https://www.dwarkeshpatel.com/feed",         "lang": "en", "category": "opinion"},
    {"name": "Lenny's Podcast",      "url": "https://www.lennysnewsletter.com/feed",      "lang": "en", "category": "opinion"},
    {"name": "Latent Space Podcast", "url": "https://www.latent.space/feed",              "lang": "en", "category": "opinion"},
    {"name": "NVIDIA AI Podcast",    "url": "https://feeds.megaphone.fm/nvidiaaipodcast", "lang": "en", "category": "opinion"},
    {"name": "TWIML AI Podcast",     "url": "https://feeds.megaphone.fm/MLN2155636147",   "lang": "en", "category": "opinion"},
    {"name": "Cognitive Revolution", "url": "https://feeds.megaphone.fm/RINTP3108857801", "lang": "en", "category": "opinion"},
    {"name": "硅谷101",              "url": "https://feeds.fireside.fm/sv101/rss",         "lang": "zh", "category": "opinion"},
    {"name": "科技早知道",            "url": "https://feeds.fireside.fm/guiguzaozhidao/rss","lang": "zh", "category": "opinion"},

# Lex Fridman	只有标题 + 1-2句描述，无文字稿	
# Dwarkesh	有部分文字转录 in feed	
# Lenny's	完整文章全文（6500+字 HTML）	高，这是 newsletter 不是 podcast
# Latent Space	完整文章全文（1000+字 HTML）	高，AINews 日报，内容很丰富


]

SCRAPE_SOURCES = [ # 很多产品主页，而拿不到blog - 之后看看 
    # [model] 无 RSS
    # {"name": "DeepSeek Blog",     "url": "https://www.deepseek.com/news",          "category": "model"},
    {"name": "阶跃星辰",          "url": "https://www.stepfun.com/news",           "category": "model"},
    {"name": "智谱AI Blog",       "url": "https://www.zhipuai.cn/news",            "category": "model"},
    {"name": "MiniMax Blog",      "url": "https://www.minimaxi.com/news",          "category": "model"},
    {"name": "Moonshot Kimi",     "url": "https://www.moonshot.cn/news",           "category": "model"},
    # {"name": "Hunyuan",           "url": "https://hunyuan.tencent.com/blog",       "category": "model"},  # 产品主页，无文章列表
    # {"name": "Tencent AI",        "url": "https://ai.tencent.com/ailab/zh/news",   "category": "model"},  # 404
    {"name": "Qwen Blog",         "url": "https://qwenlm.github.io/blog",          "category": "model"},
    {"name": "Seed ByteDance",    "url": "https://seed.bytedance.com/en/blog",     "category": "model"},
    # {"name": "快手技术",          "url": "https://www.kuaishou.com/about/news",    "category": "model"},  # 404
    {"name": "Black Forest Labs", "url": "https://bfl.ai/blog",                    "category": "model"},

    # [creative] 创意 AI 工具（无 RSS）
    {"name": "可灵 Kling",        "url": "https://app.klingai.com/cn/news",        "category": "creative"},
    {"name": "PixVerse",          "url": "https://pixverse.ai/en/blog",            "category": "creative"},
    {"name": "Higgsfield",        "url": "https://higgsfield.ai/blog",             "category": "creative"},
    {"name": "Krea",              "url": "https://www.krea.ai/blog",               "category": "creative"},
    {"name": "Recraft",           "url": "https://www.recraft.ai/blog",            "category": "creative"},
    {"name": "Fal.ai Blog",       "url": "https://blog.fal.ai",                    "category": "creative"},
    # {"name": "HeyGen Blog",       "url": "https://www.heygen.com/blog",            "category": "creative"},  # JS渲染，无静态内容
    # {"name": "ElevenLabs Blog",   "url": "https://elevenlabs.io/blog",             "category": "creative"},  # JS渲染，无静态内容
    {"name": "Pika Blog",         "url": "https://pika.art/blog",                  "category": "creative"},
    # {"name": "Ideogram Blog",     "url": "https://ideogram.ai/blog",               "category": "creative"},  # 403
    {"name": "Suno Blog",         "url": "https://suno.com/blog",                  "category": "creative"},
    {"name": "Meshy Blog",        "url": "https://www.meshy.ai/blog",              "category": "creative"},
    # {"name": "Dreamina",          "url": "https://dreamina.capcut.com",            "category": "creative"},  # 产品主页
    # {"name": "Rodin",             "url": "https://hyperhuman.deemos.com/rodin",    "category": "creative"},  # 产品主页
    {"name": "Tripo",             "url": "https://www.tripo3d.ai/blog",            "category": "creative"},
    {"name": "OpenArt",           "url": "https://openart.ai/blog",                "category": "creative"},
    # {"name": "Medeo",             "url": "https://www.medeo.app",                  "category": "creative"},  # 产品主页
    # {"name": "Flova",             "url": "https://www.flova.ai",                   "category": "creative"},  # 产品主页
    {"name": "Vidmuse",           "url": "https://vidmuse.ai/blog",                "category": "creative"},
    # {"name": "oiioii",            "url": "https://www.oiioii.ai",                  "category": "creative"},  # 产品主页
    # {"name": "tapnow",            "url": "https://www.tapnow.ai",                  "category": "creative"},  # 产品主页
    {"name": "Manus",             "url": "https://manus.im/blog",                  "category": "creative"},
    # {"name": "Genspark",          "url": "https://www.genspark.ai/blog",           "category": "creative"},  # 403
    # {"name": "剪映",              "url": "https://www.jianying.com/news",          "category": "creative"},  # 重定向到主页
    # {"name": "美图",              "url": "https://www.meitu.com/news",             "category": "creative"},  # 无文章列表
    # {"name": "即梦",              "url": "https://jimeng.jianying.com",            "category": "creative"},

    # [social]
    {"name": "Character.AI Blog", "url": "https://blog.character.ai",              "category": "social"},
    # {"name": "Replika Blog",      "url": "https://replika.com/blog",               "category": "social"},  # 404
    {"name": "Talkie",            "url": "https://www.talkie-ai.com/blog",         "category": "social"},
    # {"name": "星野",              "url": "https://www.xingyeai.com",               "category": "social"},
    # {"name": "猫箱",              "url": "https://maoxiangai.com/industry-news.html", "category": "social"}, # 好像也不大对
    # {"name": "Elys AI",           "url": "https://www.elys.live",                  "category": "social"},
    # {"name": "WayShot",           "url": "https://www.wayshot.ai",                 "category": "social"},
    # {"name": "Anuttacon",         "url": "https://www.anuttacon.com",              "category": "social"},
    # {"name": "无限谷",            "url": "https://www.infinityvalley.com",         "category": "social"},
    # {"name": "松果时刻",          "url": "https://www. songguoshike.com",            "category": "social"},
    # Loopit 仅有 App Store 页面，无法 爬取

    # [opinion] 核心人物博客（无 RSS）
    {"name": "Karpathy Blog",     "url": "https://karpathy.ai",                    "category": "opinion"},
    {"name": "Dario Amodei Blog", "url": "https://www.darioamodei.com",            "category": "opinion"},
    {"name": "Colah Blog",        "url": "https://colah.github.io",                "category": "opinion"},
    {"name": "Francois Chollet",  "url": "https://fchollet.com",                   "category": "opinion"},
    {"name": "Mustafa Suleyman",  "url": "https://mustafa-suleyman.ai",            "category": "opinion"},
    {"name": "Karina Nguyen",     "url": "https://karinanguyen.com",               "category": "opinion"},
    {"name": "Founder Park",      "url": "https://founderpark.net",                "category": "opinion"},# 创业社区
]


# [opinion] (username -> display name)
TWITTER_ACCOUNTS = {
    "sama":        "Sam Altman",
    "elonmusk":    "Elon Musk",
    "DarioAmodei": "Dario Amodei",
    "karpathy":    "Karpathy",
    "ShunyuYao12":    "Shunyu Yao",
    "tydsh":        "Yuandong Tian",
}