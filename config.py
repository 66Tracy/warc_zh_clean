# -*- coding: utf-8 -*-
"""All threshold constants, regex patterns, and keyword lists for the cleaning pipeline.

This module contains ONLY data — no business logic.
"""

import re
from dataclasses import dataclass, field
from typing import Tuple

# ============================================================================
# Optional dependency behaviour
# ============================================================================

STRICT_OPTIONAL_DEPS = False  # Set True to raise ImportError on missing optional deps

# ============================================================================
# General thresholds
# ============================================================================

MIN_TEXT_LEN = 256
FINAL_TEXT_LENGTH_RATIO_THRESHOLD = 0.5
BAD_KEYWORD_HIT_THRESHOLD = 2  # legacy, no longer used by chapter_filter (kept for back-compat)
LENGTH_RATIO_EPSILON = 1e-7

# ============================================================================
# Density rule dataclass
# ============================================================================


@dataclass(frozen=True)
class DensityRule:
    """A count-based pre-filter rule that scales with document length.

    Attributes:
        name:             Identifier used in the reject detail string.
        counter:          How to count hits.  Two forms:
                          ``"substr:<s>"``  — ``text.count(<s>)``
                          ``"regex:<pat>"`` — ``len(re.findall(<pat>, text))``
        max_per_kilo:     Maximum hits allowed per 1 000 characters (soft threshold).
        min_count:        Absolute hit count below which the rule never triggers
                          (protects short documents from false positives).
        category_exempt:  Tuple of category strings that bypass this rule.
    """

    name: str
    counter: str
    max_per_kilo: float
    min_count: int = 3
    category_exempt: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LineComboRule:
    """A keyword-combination line-deletion rule for _is_bad_line.

    Attributes:
        name:      Human-readable identifier for debugging.
        all_of:    Substrings that must ALL be present in the line.
        any_of:    At least one of these substrings must be present
                   (empty tuple means no constraint).
        max_len:   Rule only fires when ``len(line) < max_len``.
                   ``None`` means no length constraint.
        lowercase: If True, apply ``line.lower()`` before matching.
    """

    name: str
    all_of: tuple = ()
    any_of: tuple = ()
    max_len: int | None = None
    lowercase: bool = False

# ============================================================================
# Category downsampling
# ============================================================================

ENABLE_CATEGORY_DOWNSAMPLE = False
CATEGORY_DOWNSAMPLE_RATIOS = {
    "生活": 0.1,
    "视频": 0.01,
    "游戏": 0.1,
    "娱乐": 0.1,
    "影视": 0.1,
    "购物": 0.2,
}
CATEGORY_BLOCKLIST = ["赌博/色情/非法"]

# ============================================================================
# Zlib compression thresholds
# ============================================================================

ZLIB_FULL_THRESHOLD = 4.0
ZLIB_BLOCK_THRESHOLD = 3.5
ZLIB_BLOCK_MIN_RAW_LEN = 128
ZLIB_BLOCK_SIZE = 500
ZLIB_REPEAT_BLOCK_MIN = 2
ZLIB_REPEAT_BLOCK_FRACTION = 0.3

# ============================================================================
# Repetition thresholds (line / paragraph)
# ============================================================================

DUPLICATE_LINE_RATIO = 0.4
DUPLICATE_LINE_CHAR_RATIO = 0.2
DUPLICATE_PARA_RATIO = 0.45
DUPLICATE_PARA_CHAR_RATIO = 0.35

# ============================================================================
# Pre-filtering thresholds
# ============================================================================

PRE_ELLIPSIS_LINE_LIMIT = 8
PRE_DATETIME_DENSITY_LIMIT = 4
PRE_BLANK_ZH_ZH_LIMIT = 50
PRE_LANG_TRANS_LIMIT = 30
PRE_ELLIPSIS_COUNT_LIMIT = 15
PRE_NGRAM_5_THRESHOLD = 20
PRE_NGRAM_15_THRESHOLD = 5
PRE_FAN2JIAN_DISTANCE_RATIO = 0.1
PRE_DATE_HITS_COUNT_LIMIT = 20
PRE_DATE_HITS_CHAR_RATIO = 0.2
PRE_MB_PATTERN_LIMIT = 8
PRE_EMPTY_PAREN_LIMIT = 8
PRE_QUESTION_MARK_LIMIT = 20
PRE_NON_PRINTABLE_RATIO = 0.07
PRE_REPLY_DAY_LIMIT = 5
PRE_EXCL_QUESTION_LIMIT = 30
PRE_SEAT_LIMIT = 40
PRE_REPLY_MIN_LIMIT = 5
PRE_REPLY_HOUR_LIMIT = 5
PRE_MACAO_LIMIT = 20
PRE_EPILEPSY_LIMIT = 10
PRE_BRACKET_LIMIT = 50
PRE_LOTTERY_LIMIT = 10
PRE_BET_LIMIT = 5
PRE_MAX_LINE_LEN_LIMIT = 12
PRE_MEAN_LINE_LEN_LIMIT = 4
PRE_DUPLICATE_LINE_COUNT_LIMIT = 6
PRE_URL_COUNT_LIMIT = 5
PRE_EMAIL_COUNT_LIMIT = 3
PRE_QQ_COUNT_LIMIT = 6
PRE_WECHAT_COUNT_LIMIT = 6
PRE_ELLIPSIS_UNICODE_LIMIT = 20
PRE_ELLIPSIS_ASCII_LIMIT = 10
PRE_DATE_BRACKET_LIMIT = 15  # legacy constant kept for reference; rule now in MISC_DENSITY_RULES

# ============================================================================
# Density rules (MISC_DENSITY_RULES)
#
# Anchored at a "typical 2000-char document":
#   max_per_kilo  ≈ old_absolute_limit / 2.0
#   min_count     = max(3, old_absolute_limit // 2)
#
# counter syntax:
#   "substr:<s>"  -> text.count(<s>)
#   "regex:<pat>" -> len(re.findall(<pat>, text))
# ============================================================================

MISC_DENSITY_RULES: list = [
    # ---- ellipsis lines ----
    # old: lines ending "..." or "…" > PRE_ELLIPSIS_LINE_LIMIT (8)
    # Note: this is applied to the lines list, handled via regex on full text
    # Approximated as: count of "\n...\n" or trailing ellipsis patterns
    DensityRule(
        name="ellipsis_line",
        counter=r"regex:(?m)(?:\.\.\.|…)\s*$",
        max_per_kilo=4.0,
        min_count=4,
    ),
    # ---- datetime stamps "YYYY-MM-DD HH:MM:SS" ----
    # old: >= PRE_DATETIME_DENSITY_LIMIT (4)
    DensityRule(
        name="datetime_stamp",
        counter=r"regex:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
        max_per_kilo=2.0,
        min_count=3,
    ),
    # ---- spaces between CJK characters ----
    # old: > PRE_BLANK_ZH_ZH_LIMIT (50)
    DensityRule(
        name="blank_zh_zh",
        counter=r"regex:[一-鿿]\s[一-鿿]",
        max_per_kilo=25.0,
        min_count=25,
    ),
    # ---- language transitions CJK-alpha-CJK ----
    # old: > PRE_LANG_TRANS_LIMIT (30)
    DensityRule(
        name="lang_trans",
        counter=r"regex:[一-鿿][a-zA-Z][一-鿿]",
        max_per_kilo=15.0,
        min_count=15,
    ),
    # ---- ASCII ellipsis "..." count ----
    # old: >= PRE_ELLIPSIS_COUNT_LIMIT (15)
    DensityRule(
        name="ellipsis_ascii",
        counter="substr:...",
        max_per_kilo=7.0,
        min_count=7,
    ),
    # ---- MB pattern "\d+mb" ----
    # old: > PRE_MB_PATTERN_LIMIT (8), exempt 编程/IT
    DensityRule(
        name="mb_pattern",
        counter=r"regex:\d+\s?mb",
        max_per_kilo=4.0,
        min_count=4,
        category_exempt=("编程/IT",),
    ),
    # ---- empty parens "()" ----
    # old: >= PRE_EMPTY_PAREN_LIMIT (8), exempt 编程/IT (also "`" check handled in code)
    DensityRule(
        name="empty_paren",
        counter="substr:()",
        max_per_kilo=4.0,
        min_count=4,
        category_exempt=("编程/IT",),
    ),
    # ---- "吗？" question marks ----
    # old: >= PRE_QUESTION_MARK_LIMIT (20)
    DensityRule(
        name="question_mark",
        counter="substr:吗？",
        max_per_kilo=10.0,
        min_count=10,
    ),
    # ---- "天前回复" forum noise ----
    # old: >= PRE_REPLY_DAY_LIMIT (5)
    DensityRule(
        name="reply_day",
        counter="substr:天前回复",
        max_per_kilo=2.5,
        min_count=3,
    ),
    # ---- "！" + "？" combined ----
    # old: >= PRE_EXCL_QUESTION_LIMIT (30)
    DensityRule(
        name="excl_question",
        counter=r"regex:[！？]",
        max_per_kilo=15.0,
        min_count=15,
    ),
    # ---- "座" seat indicator ----
    # old: >= PRE_SEAT_LIMIT (40)
    DensityRule(
        name="seat",
        counter="substr:座",
        max_per_kilo=20.0,
        min_count=20,
    ),
    # ---- "分钟前回复" ----
    # old: >= PRE_REPLY_MIN_LIMIT (5)
    DensityRule(
        name="reply_min",
        counter="substr:分钟前回复",
        max_per_kilo=2.5,
        min_count=3,
    ),
    # ---- "小时前回复" ----
    # old: >= PRE_REPLY_HOUR_LIMIT (5)
    DensityRule(
        name="reply_hour",
        counter="substr:小时前回复",
        max_per_kilo=2.5,
        min_count=3,
    ),
    # ---- "澳门" Macau gambling signal ----
    # old: >= PRE_MACAO_LIMIT (20)
    DensityRule(
        name="macao",
        counter="substr:澳门",
        max_per_kilo=10.0,
        min_count=10,
    ),
    # ---- "癫痫病" medical spam ----
    # old: >= PRE_EPILEPSY_LIMIT (10)
    DensityRule(
        name="epilepsy",
        counter="substr:癫痫病",
        max_per_kilo=5.0,
        min_count=5,
    ),
    # ---- "【" full-width bracket ----
    # old: >= PRE_BRACKET_LIMIT (50)
    DensityRule(
        name="bracket",
        counter="substr:【",
        max_per_kilo=25.0,
        min_count=25,
    ),
    # ---- "彩票" lottery ----
    # old: >= PRE_LOTTERY_LIMIT (10)
    DensityRule(
        name="lottery",
        counter="substr:彩票",
        max_per_kilo=5.0,
        min_count=5,
    ),
    # ---- "买球" sports betting ----
    # old: >= PRE_BET_LIMIT (5)
    DensityRule(
        name="bet",
        counter="substr:买球",
        max_per_kilo=2.5,
        min_count=3,
    ),
    # ---- "<URL>" placeholder ----
    # old: > PRE_URL_COUNT_LIMIT (5)
    DensityRule(
        name="url_placeholder",
        counter="substr:<URL>",
        max_per_kilo=2.5,
        min_count=3,
    ),
    # ---- "<EMAIL>" placeholder ----
    # old: > PRE_EMAIL_COUNT_LIMIT (3)
    DensityRule(
        name="email_placeholder",
        counter="substr:<EMAIL>",
        max_per_kilo=1.5,
        min_count=3,
    ),
    # ---- "QQ" account spam ----
    # old: > PRE_QQ_COUNT_LIMIT (6)
    DensityRule(
        name="qq",
        counter="substr:QQ",
        max_per_kilo=3.0,
        min_count=3,
    ),
    # ---- "微信" WeChat spam ----
    # old: > PRE_WECHAT_COUNT_LIMIT (6)
    DensityRule(
        name="wechat",
        counter="substr:微信",
        max_per_kilo=3.0,
        min_count=3,
    ),
    # ---- "…" unicode ellipsis ----
    # old: >= PRE_ELLIPSIS_UNICODE_LIMIT (20)
    DensityRule(
        name="ellipsis_unicode",
        counter="substr:…",
        max_per_kilo=10.0,
        min_count=10,
    ),
    # ---- "[DD-DD]" date bracket pattern ----
    # old: >= PRE_DATE_BRACKET_LIMIT (15)
    DensityRule(
        name="date_bracket",
        counter=r"regex:\[\d{2}-\d{2}\]",
        max_per_kilo=7.0,
        min_count=7,
    ),
]

# ============================================================================
# Bad keyword scoring
# ============================================================================

# Scoring thresholds for bad-keyword weighted sum filter
BAD_KEYWORD_SCORE_MIN: float = 3.0          # absolute minimum score to trigger
BAD_KEYWORD_SCORE_PER_KILO: float = 1.0    # score per 1 000 chars to trigger

# Per-keyword weights.  Keys not present default to 1.0.
# weight 2.0  -> unambiguous strong garbage signal (core porn/gambling terms)
# weight 0.5  -> edge terms that appear often in legitimate text
BAD_KEYWORD_WEIGHTS: dict = {
    # ---- core pornographic terms (weight 2.0) ----
    "操逼": 2.0, "肏你": 2.0, "肏死": 2.0, "操死": 2.0, "狂操": 2.0,
    "狂插": 2.0, "强奸": 2.0, "强暴": 2.0, "轮奸": 2.0, "轮暴": 2.0,
    "强jian": 2.0, "乱伦": 2.0, "乱交": 2.0, "群交": 2.0, "肛交": 2.0,
    "口交": 2.0, "阴道": 2.0, "阴茎": 2.0, "阴唇": 2.0, "阴蒂": 2.0,
    "肉棒": 2.0, "鸡巴": 2.0, "鸡吧": 2.0, "屌": 2.0, "淫荡": 2.0,
    "淫乱": 2.0, "淫穴": 2.0, "骚逼": 2.0, "骚屄": 2.0, "嫩逼": 2.0,
    "肏": 2.0, "插逼": 2.0, "插比": 2.0, "屄": 2.0, "后庭": 2.0,
    "兽交": 2.0, "兽奸": 2.0, "幼交": 2.0, "幼女": 2.0, "幼男": 2.0,
    "色情网站": 2.0, "色情片": 2.0, "成人网站": 2.0, "成人av": 2.0,
    "av视频": 2.0, "av在线": 2.0, "日本av": 2.0, "欧美av": 2.0,
    "porn": 2.0, "hardcore": 2.0, "incest": 2.0,
    # ---- core gambling/illegal terms (weight 2.0) ----
    "澳门威尼斯人": 2.0, "澳门新葡京": 2.0, "皇冠博彩": 2.0, "皇冠正网": 2.0,
    "在线博彩": 2.0, "网赌": 2.0, "线上买球": 2.0, "购彩": 2.0,
    "平台买球": 2.0, "投注": 2.0, "押注": 2.0, "开奖直播现场": 2.0,
    "彩票官方": 2.0, "澳门彩": 2.0, "时时彩": 2.0, "竞彩预测": 2.0,
    "法轮功": 2.0, "失身粉": 2.0, "迷奸粉": 2.0, "迷奸药": 2.0,
    "摇头丸": 2.0, "morphine": 2.0, "narcotic": 2.0,
    # ---- edge/borderline terms (weight 0.5) ----
    # These commonly appear in legitimate contexts (literature, medicine, news)
    "按摩": 0.5,        # massage — health/medical context common
    "情趣用品": 0.5,    # can appear in news/regulation context
    "白痴": 0.5,        # insult but also casual/literary use
    "卧槽": 0.5,        # mild expletive in casual Chinese text
    "草泥马": 0.5,      # internet slang, often not explicitly sexual
    "傻逼": 0.5,        # common mild insult in casual text
    "婊子": 0.5,        # can appear in literary/news context
    "人渣": 0.5,        # common derogatory but widely used in news
    "无耻": 0.5,        # common moral judgment in normal text
    "裸露": 0.5,        # nudity — art/news/medical context common
    "写真": 0.5,        # photo set — legitimate photography term
    "调教": 0.5,        # training/taming — legitimate in animal/education context
    "偷拍": 0.5,        # candid photography — can appear in news
    "丝袜": 0.5,        # stockings — fashion context common
    "性生活": 0.5,      # sexual health — medical/educational context
    "精子": 0.5,        # biology/medical
    "乳房": 0.5,        # anatomy — medical/literary context
    "高潮": 0.5,        # climax — also used in music/drama/literature
    "推油": 0.5,        # massage term — can appear in normal context
    "自拍": 0.5,        # selfie — completely normal term
    "在线视频": 0.5,    # online video — ubiquitous normal term
    "国产精品": 0.5,    # "domestic quality products" — legitimate e-commerce
    "sm": 0.5,          # abbreviation with many legitimate uses
    "美少女": 0.5,      # can appear in anime/cultural context
    "人妻": 0.5,        # married woman — in literature/drama/news
    "发情": 0.5,        # can appear in biology/animal context
}

# ============================================================================
# Post-filtering thresholds
# ============================================================================

POST_BULLET_LINE_RATIO = 0.85
POST_BULLET_LINE_MIN = 8
POST_LONG_SENT_LEN = 80
POST_TIME_HHMM_LIMIT = 6
POST_TRUNC_LINE_RATIO = 0.6

# ============================================================================
# Document basic quality (is_needed_document)
# ============================================================================

WHITESPACE_RATIO_MAX = 0.2
NON_CJK_RATIO_MAX = 0.5
BULLET_LINE_RATIO_MAX = 0.9
ELLIPSIS_LINE_RATIO_MAX = 0.2

# ============================================================================
# Line cleaning thresholds (from line_rules.py)
# ============================================================================

LINE_CONTACT_INFO_MAX_LEN = 50
LINE_CONTACT_KEYWORDS = ["QQ", "微信", "手机", "电话", "座机", "qq", "wx"]
LINE_CONTACT_KEYWORD_MIN_HITS = 1

LINE_COLON_END_MAX_LEN = 10
LINE_BRACKET_MAX_LEN = 10
LINE_SHORT_ZH_MAX_LEN = 4
LINE_SHORT_EN_MAX_LEN = 12
LINE_SHORT_EN_MAX_WORDS = 2
LINE_KEYWORD_CHECK_MAX_LEN = 18
LINE_BULLET_MAX_LEN = 10
LINE_WEBSITE_MAINT_MAX_LEN = 40
LINE_READ_FULL_MAX_LEN = 20
LINE_REGISTER_MAX_LEN = 40
LINE_WECHAT_FOLLOW_MAX_LEN = 40
LINE_PUBLISH_INFO_MAX_LEN = 40
LINE_VERY_SHORT_MAX_LEN = 4
LINE_PAREN_NUM_MIN = 20
LINE_DATETIME_RATIO = 0.4
LINE_QUOTE_MIN = 5
LINE_GT_MIN = 2
LINE_BRACKET_DENSE_BRACKET = 3
LINE_PIPE_MIN = 3
LINE_TAIL_LAST_LINE_MAX_LEN = 30

# ============================================================================
# Line combo rules (keyword-combination line-deletion rules)
# ============================================================================

LINE_COMBO_RULES: list = [
    # ---- navigation bars ----
    LineComboRule(
        name="nav_home_end",
        all_of=("首页", "尾页", "1"),
    ),
    LineComboRule(
        name="nav_guillemet",
        all_of=("«", "1", "2"),
    ),
    # ---- address line ----
    LineComboRule(
        name="address_line",
        all_of=("地址：",),
    ),
    # ---- porn video ----
    LineComboRule(
        name="porn_video",
        all_of=("污", "视频"),
    ),
    # ---- gambling/adult keywords combined with "app" ----
    LineComboRule(
        name="gambling_app",
        any_of=("电竞", "体育", "博", "彩", "大片", "竞猜", "bob", "18禁",
                "直播", "传媒", "真人", "赚钱", "无码", "影视", "高清", "提现"),
        all_of=("app",),
        lowercase=True,
    ),
    # ---- sports + gambling without app ----
    LineComboRule(
        name="sports_gambling",
        all_of=("体育", "博"),
    ),
    # ---- website maintenance / font setting (short lines only) ----
    LineComboRule(
        name="website_maint",
        all_of=("网站", "维护"),
        max_len=LINE_WEBSITE_MAINT_MAX_LEN,
    ),
    LineComboRule(
        name="font_setting",
        all_of=("字体：",),
        max_len=LINE_WEBSITE_MAINT_MAX_LEN,
    ),
    # ---- read full text (short lines only) ----
    LineComboRule(
        name="read_full",
        all_of=("阅读", "全文"),
        max_len=LINE_READ_FULL_MAX_LEN,
    ),
    # ---- view & reply ----
    LineComboRule(
        name="view_reply",
        all_of=("查看:", "回复:"),
    ),
    # ---- register + login/password combos (short lines only) ----
    LineComboRule(
        name="register_login",
        all_of=("注册",),
        any_of=("登录", "登陆", "密码"),
        max_len=LINE_REGISTER_MAX_LEN,
    ),
    LineComboRule(
        name="phone_fax",
        all_of=("电话", "传真"),
        max_len=LINE_REGISTER_MAX_LEN,
    ),
    LineComboRule(
        name="prev_article",
        all_of=("上篇：",),
        max_len=LINE_REGISTER_MAX_LEN,
    ),
    LineComboRule(
        name="next_article",
        all_of=("下篇：",),
        max_len=LINE_REGISTER_MAX_LEN,
    ),
    # ---- WeChat follow (short lines only) ----
    LineComboRule(
        name="wechat_follow",
        all_of=("关注", "微信"),
        max_len=LINE_WECHAT_FOLLOW_MAX_LEN,
    ),
    # ---- publish info (short lines only) ----
    LineComboRule(
        name="publish_info",
        all_of=("本文", "发表于"),
        max_len=LINE_PUBLISH_INFO_MAX_LEN,
    ),
    # ---- next page with number ----
    LineComboRule(
        name="next_page_num",
        all_of=("下一页", "1"),
    ),
    # ---- SEO ranking ----
    LineComboRule(
        name="seo_rank",
        all_of=("seo", "排"),
        lowercase=True,
    ),
    # ---- Macao gambling ----
    LineComboRule(
        name="macao_casino",
        all_of=("澳门",),
        any_of=("葡", "莆"),
    ),
    LineComboRule(
        name="macao_venetian",
        all_of=("澳门", "威", "尼"),
    ),
]

# ============================================================================
# Tail/head cleanup keywords
# ============================================================================

TAIL_LAST_LINE_PATTERNS = (
    r"\<URL\>|电脑版|许可证：|本文关键词：|⏬|在线咨询：|扫码"
    r"|本网站|转载|站点|返回列表|在线人数|关闭窗口|微信|QQ|qq"
    r"|抖音|公众号|电话："
)

TAIL_BAD_KEYWORDS = (
    r"点击：|http://|https://|马上登录|友情提醒：|在线咨询|<URL>"
    r"|\.com|相关推荐：|\.cn|请先登录|微信扫一扫|A片|微信朋友圈"
    r"|微信公众号|电话：|作者：|本站|ICP备|在线客服|本文关键词："
    r"|原创内容|需要登录|全球华人|长按图片|不得转载"
)

HEAD_BAD_KEYWORDS = r"点击：|微信扫一扫|微信朋友圈|作者：|本站|在线客服"

# ============================================================================
# Detail field name
# ============================================================================

DETAIL_FIELD = "new_filter_detail"

# ============================================================================
# Extraction padding chars
# ============================================================================

URL_PAD_CHAR = "￥"
EMAIL_PAD_CHAR = "龥"

# ============================================================================
# Raw pattern strings
# ============================================================================

EMAIL_PATTERN = (
    r"(?<=[^0-9a-zA-Z\!\#\$\%\&\'\*\+\-\/\=\?\^\_\`\{\|\}\~\-])"
    r"([a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+(?:\.[a-zA-Z0-9]+)*\.[a-zA-Z0-9]{2,6})"
    r"(?=[^0-9a-zA-Z\!\#\$\%\&\'\*\+\-\/\=\?\^\_\`\{\|\}\~\-])"
)

EMAIL_DOMAIN_PATTERN = r"(?<=@)([0-9a-zA-Z]+)(?=\.)"

URL_PATTERN = (
    r"(?<=[^.])((?:(?:https?|ftp|file)://|(?<![a-zA-Z\-\.])www\.)"
    r"[\-A-Za-z0-9\+&@\(\)#/%\?\=\~_|!:\,\.\\;]+[\-A-Za-z0-9\+&@#/%=\~_\|])"
    r"(?=[<\u4E00-\u9FA5\uffe5\u201c\uff0c\u3002\uff1b\uff01\uff1f\u3001\u201c\u201d\u2018\u2019>\uff08\uff09\u2014\u300a\u300b\u2026\u25cf \t\n])"
)

# ============================================================================
# Pre-compiled regex objects
# ============================================================================

URL_RE = re.compile(URL_PATTERN)
EMAIL_RE = re.compile(EMAIL_PATTERN)
EMAIL_DOMAIN_RE = re.compile(EMAIL_DOMAIN_PATTERN)
SPACES_4_RE = re.compile(r"\s{4,}")
POST_SPLIT_RE = re.compile(
    r'[\sa-zA-Z0-9!\"\#\$\%&\'\(\)\*\+\,\-\.\/\:;<\>\?\@\[\\\]\^\_`\{\|\}\~'
    r'！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—''‛""„‟…‧﹏\\.]'
)
TIME_HHMM_RE = re.compile(r'\d{2}[:：]\d{2}')
TRUNC_LINE_RE = re.compile(r"[\u4e00-\u9fff]\n")

# ============================================================================
# Rule regex patterns (noise/spam detection)
# ============================================================================

dummy_words_rules = re.compile(
    r"体育官方|463cc|免费加速|暂无讨论|点击率：|天 天 彩|神 算 子|听书app|公众号：|私密.*?聊天|世界杯竞猜|打开网易新闻|最新章节|网盘地址s|网盘链接|more\+|拿证快|好友发表于|浏览量：|vip推荐|预计阅读时间|浏览次数:|免费发布|\d次查看|快速登入|云盘链接|推荐度：|下载到电脑|浏览：\d|评论：\d|代孕|助孕|加导师|老师微信|导师微信|包性别|包男孩|发表于\s\d|\d次查看|免费发布|请拨打|在线咨询|文章ID：|搜索结果包含|请稍等片刻|本商品类别内|可信网站:|所有卖家|mg集团|点击下载|至尊国际|竞猜官方|9球网|[㊣㊛㊚㊤㊦㊥㊧㊨㊢㊎㊒㊔㊪㊐㊋㊠㊙㊬㊑㊊㊡㊯㊕㊫㊰㊩㊓㊌㊘㊏㊞㊜㊝㊭㊗㊍㊖㊟㊮㊀㊁㊂㊃㊄㊅㊆㊇㊈㊉]|下一主题：|上一主题：|官方版|aoa|未删版|文章ID|金沙国际|㊈|service phone|网站公告|惠泽网|㊁|catalogs:|timestamp:|米乐|x201d;|本文已被阅读|免责声明：|相关词条：|后台编辑|国际网站|奥门|xa0;|，、|灰产排|88网|在线观看|免费在线|更新时间 |摸j|香港神算子|微博/知乎|秒收录|灰色排名|灰色词|访问次数：|备案号：|次浏览|今日/知乎|免费在线|买球|本章未完|章节错误|在线精品|久热草|全部文章|现在的位置|中字资源|游戏大厅|热点事件:|资源网|天天免费|彩票官方|威尼斯人|原标题：|福利领取|香港马会|今日访问|申博|在线播放|免费版观看|赢钱.*?提现|\[注册\]|上一章.*?下一章|发表时间：|购彩|人气：|完整资源|p网盘|久久影院|中字资源|久久人|次播放|人已点赞|㊎|六盒彩|肖三码|三肖|高清资源|彩6|usdt|彩六|ag8|ag真人|学习资料下载|h全彩|…【|联系我们|• \d{4}\-\d{2}|•\d{4}\-\d{2}|\[\d{4}\-\d{2}|\[\d{2}\-\d{2}\]|显示全部楼层|体育官方网站|涓\?|点我进入|亚体育|\- 知乎|资源分享|在线观看|关注领取|返回首页|编辑本段|免费编辑|成人影视|联系人：|请输入计算结果|pc蛋蛋|您的位置|0P网盘|啪到|点击购买|当前位置|白癜风|博乐|微:\d|网赌|登录后才可以|人来访过|加入书架|威尼斯城|点击量：|亚搏|验证码：|\?姝|百度云资源|澳门彩|㊄|fun88|update:|mg游戏|联博|微信：|加速器|真人网|扑体育|网盘更新|小时内删除|免费观看|澳门网|㊘|文章ID：|电子官网|最新新闻:|热门新闻:|``` ```|kok|本文链接|发布日期:|bob竞猜|阅读下一篇|查看下一篇|宝体育|前往购买|\_腾讯网|帖子热度|新葡|澳门威斯人|bob.*?体育|最新章节全文|欧博|预测网|\.com\.com|竞彩预测|免费阅读|信誉老平台|上一篇文章|下一篇文章|久久精品|六玄网|官网入口|福利.*?影视|热线：|百度云高清|全集百度云|亚博|亚洲必赢|免费无广告|无弹窗|免费在线观看|确定不再关注|金沙js|澳博|还看过以下|电竞app|下頁|app体育|app电竞|体育app|\[上一篇\]|\[下一篇\]|新京浦|无匹配数据|高清迅雷下载|当前位置.*?>|转载请注明|请勿转载|第\d+楼|文章来源：|输入验证码|莆京|新浦金|您现在的位置|文字大小：|体育全站|posted in|posted on|请扫一扫|手机：\d|全部评论|P网盘|ip安备|搏全站|后台属性模板|entry was posted|打印本页|手机:\d|已关闭评论|电话：\d|电话:\d|[a-z0-9A-Z+/\n=]{32}|qq:\d|qq：\d|淘口令|立即购买|体育官网|全国统一电话|返回上一|务热线：|邮箱：|ＱＱ：|tel：|网安备|查看全部|关键字：|icp证|icp备|next article|发布时间:|发布时间：|previous article|全文免费阅读|您现在的位置|content details|您当前所在位置|时效评分：|4399高清在线观看免费大全|点击添加图片|画中画广告|【返回列表】|【推荐阅读】|本文关键词：|浏览人次：|还能够输入\d+字|浏览人气:|提取码：|扫描二维码|发布日期：|请输入计算结果|广告: |忘记密码？|http[:]/|https[:]/|\(继续阅读|(使用).*?(cookie)|摘要：|阅读：\d+|(浏览).*?(cookie)|(浏览).*?(支持)|免费下载|充值入口|词条.*编辑|声明:|更新时间：|千万别错过!|淘宝.*淘|点击:.*?\d+|咨询热线|收藏本[站文网]|点击.*关注|当前位置[:：]|发表评论|qq咨询|网.*登录|[^0-9]／[^0-9]| >> |您的信息|电邮发送|点此编辑|点击数：|欢迎关注|地址.*不会.*公开|推荐阅读：|浏览:\d+|提示：|注册.*会员|内容.*来自|点击输入|您.*评论|您.*留言|您.*帳號''|来源：|您.*[消信]息|每页\d+条|请注明出处：|微信号：|了解.*请联[系络]|微信公众号：|欢迎.*讨论"
)

end_prompts = re.compile(
    r"[上下]一[页个篇条][： :]|\(c\).*?(版权)|(权).*?(所有)|声明：|禁止.*转载|如有侵权|©|(未经).*?(许可)|未经.*授权|(本[文网站]).*?(来源)|(本[文网站]).*?(转载)|(本[文网站]).*?(侵权)|(欢迎).*?(咨询)|(欢迎).*?(联系)|了解详情|查看详情|加.*微信|了解更多|免责声明|本[站网].*联系|联系.*本[站网人]]|关注我们|加.*微信|阅读更多|previous post|[上下]一新闻"
)

# ============================================================================
# Bad keyword list
# ============================================================================

BAD_KEYWORDS = [
    "爱女人", "爱液", "野战", "按摩棒", "夜色聊人", "爆草", "包二奶", "暴干", "暴奸",
    "暴乳", "爆乳", "暴淫", "屄", "被操", "被插", "被干", "逼奸", "仓井空", "插暴",
    "操逼", "操黑", "操烂", "肏你", "肏死", "操死", "操我", "厕奴", "插比", "插b",
    "插逼", "插进", "插你", "插我", "插阴", "潮吹", "潮喷", "成人dv", "成人电影",
    "成人论坛", "成人小说", "成人电", "成人卡通", "成人聊", "成人片", "成人视",
    "成人图", "成人文", "成人小", "成人色情", "成人网站", "成人文学", "艳情小说",
    "成人游戏", "吃精", "赤裸", "扌由插", "抽一插", "春药", "大波", "大力抽送",
    "大乳", "荡妇", "荡女", "盗撮", "多人轮", "发浪", "放尿", "肥逼", "粉穴",
    "封面女郎", "风月大陆", "干死你", "干穴", "肛交", "肛门", "龟头", "裹本",
    "国产av", "好嫩", "豪乳", "黑逼", "后庭", "后穴", "虎骑", "花花公子",
    "换妻俱乐部", "黄片", "几吧", "鸡吧", "鸡巴", "鸡奸", "寂寞男", "寂寞女",
    "妓女", "集体淫", "奸情", "叫床", "脚交", "金鳞岂是池中物", "金麟岂是池中物",
    "精液", "就去日", "巨屌", "菊花洞", "菊门", "巨奶", "巨乳", "菊穴", "开苞",
    "口爆", "口活", "口交", "口射", "口淫", "裤袜", "狂操", "狂插", "浪逼", "浪妇",
    "浪叫", "浪女", "狼友", "聊性", "流淫", "铃木麻", "凌辱", "漏乳", "露b", "乱交",
    "乱伦", "轮暴", "轮操", "轮奸", "裸陪", "买春", "美逼", "美少妇", "美乳", "美腿",
    "美穴", "美幼", "秘唇", "迷奸", "密穴", "蜜穴", "蜜液", "摸奶", "摸胸", "母奸",
    "奈美", "奶子", "男奴", "内射", "嫩逼", "嫩女", "嫩穴", "捏弄", "女优", "炮友",
    "砲友", "喷精", "屁眼", "品香堂", "前凸后翘", "强jian", "强暴", "强奸处女",
    "情趣用品", "情色", "拳交", "全裸", "群交", "惹火身材", "人妻", "人兽", "日逼",
    "日烂", "肉棒", "肉逼", "肉唇", "肉洞", "肉缝", "肉棍", "肉茎", "肉具", "揉乳",
    "肉穴", "肉欲", "乳爆", "乳房", "乳沟", "乳交", "乳头", "三级片", "骚逼", "骚比",
    "骚女", "骚水", "骚穴", "色逼", "色界", "色猫", "色盟", "色情网站", "色区",
    "色色", "色诱", "色欲", "色b", "少年阿宾", "少修正", "射爽", "射颜", "食精",
    "释欲", "兽奸", "兽交", "手淫", "兽欲", "熟妇", "熟母", "熟女", "爽片",
    "爽死我了", "双臀", "死逼", "丝袜", "丝诱", "松岛枫", "酥痒", "汤加丽", "套弄",
    "体奸", "体位", "舔脚", "舔阴", "调教", "偷欢", "偷拍", "推油", "脱内裤", "文做",
    "我就色", "无码", "舞女", "无修正", "吸精", "夏川纯", "相奸", "小逼", "校鸡",
    "小xue", "写真", "性感妖娆", "性感诱惑", "性虎", "性饥渴", "性技巧", "性交",
    "性奴", "性虐", "性息", "性欲", "胸推", "穴口", "学生妹", "穴图", "亚情", "颜射",
    "阳具", "要射了", "夜勤病栋", "一本道", "一夜欢", "一夜情", "一ye情", "阴部",
    "淫虫", "阴唇", "淫荡", "阴道", "淫电影", "阴阜", "淫妇", "淫河", "阴核", "阴户",
    "淫贱", "淫叫", "淫教师", "阴茎", "阴精", "淫浪", "淫媚", "淫糜", "淫魔", "淫母",
    "淫女", "淫虐", "淫妻", "淫情", "淫色", "淫声浪语", "淫兽学园", "淫书",
    "淫术炼金士", "淫水", "淫娃", "淫威", "淫亵", "淫样", "淫液", "淫照", "阴b",
    "应召", "幼交", "幼男", "幼女", "欲火", "欲女", "玉女心经", "玉蒲团", "玉乳",
    "欲仙欲死", "玉穴", "援交", "原味内衣", "援助交际", "张筱雨", "招鸡", "招妓",
    "中年美妇", "抓胸", "自拍", "自慰", "作爱", "18禁", "99bb", "a4u", "a4y", "adult",
    "amateur", "anal", "a片", "fuck", "gay片", "g点", "g片", "hardcore", "h动画",
    "h动漫", "incest", "porn", "secom", "sexinsex", "sm女王", "xiao77", "xing伴侣",
    "tokyohot", "yin荡", "贱人", "装b", "大sb", "傻逼", "傻b", "煞逼", "煞笔", "刹笔",
    "傻比", "沙比", "欠干", "婊子养的", "我日你", "我操", "我草", "卧艹", "卧槽",
    "爆你菊", "艹你", "cao你", "你他妈", "真他妈", "别他吗", "草你吗", "草你丫",
    "操你妈", "擦你妈", "操你娘", "操他妈", "日你妈", "干你妈", "干你娘", "娘西皮",
    "狗操", "狗草", "狗杂种", "狗日的", "操你祖宗", "操你全家", "操你大爷", "妈逼",
    "你麻痹", "麻痹的", "妈了个逼", "马勒", "狗娘养", "贱比", "贱b", "下贱", "死全家",
    "全家死光", "全家不得好死", "全家死绝", "白痴", "无耻", "sb", "杀b", "你吗b",
    "你妈的", "婊子", "贱货", "人渣", "混蛋", "媚外", "性伴侣", "男公关", "火辣",
    "精子", "射精", "诱奸", "强奸", "做爱", "性爱", "发生关系", "按摩", "快感",
    "处男", "猛男", "少妇", "屌", "屁股", "下体", "内裤", "浑圆", "咪咪", "发情",
    "白嫩", "粉嫩", "兽性", "风骚", "呻吟", "sm", "阉割", "高潮", "裸露", "不穿",
    "一丝不挂", "脱光", "干你", "干死", "我干", "裙中性运动", "乱奸", "乱伦类",
    "乱伦小", "伦理大", "伦理电影", "伦理毛", "伦理片", "裸聊", "裸聊网", "裸体写真",
    "裸舞视", "裸照", "美女裸体", "美女写真", "美女上门", "美艳少妇", "妹按摩",
    "妹上门", "迷幻药", "迷幻藥", "迷昏口", "迷昏药", "迷昏藥", "迷魂香", "迷魂药",
    "迷魂藥", "迷奸粉", "迷奸药", "迷情粉", "迷情水", "迷情药", "迷药", "迷藥",
    "谜奸药", "骚妇", "骚货", "骚浪", "骚嘴", "色电影", "色妹妹", "色情表演",
    "色情电影", "色情服务", "色情图片", "色情小说", "色情影片", "色情片", "色视频",
    "色小说", "性服务", "性福情", "性感少", "性伙伴", "性交视频", "性交图片",
    "性奴集中营", "阴蒂", "阴间来电", "阴茎增大", "阴茎助勃", "阴毛", "陰唇",
    "陰道", "陰戶", "淫荡美女", "淫荡视频", "淫荡照片", "淫乱", "淫靡", "淫魔舞",
    "淫情女", "淫肉", "淫騷妹", "淫兽", "淫兽学", "淫穴", "morphine", "摇头丸",
    "乖乖粉", "narcotic", "麻醉药", "精神药品", "干逼", "你妈逼", "草你妈", "艹你妈",
    "草泥马", "曹尼玛", "失身粉", "淫荡自慰器", "啪啪", "射了", "自慰棒", "肉肏",
    "肏", "抽插", "抠弄", "小穴", "制服诱惑", "干到尖叫", "大色窝", "夜夜撸",
    "色播播", "同城交友", "虐奸", "骚屄", "成av人", "天天色", "天天操", "狠狠日",
    "大香蕉网", "人人操", "伊人久久", "人人干免费在线视频", "传奇私服", "热血传奇",
    "传奇私服网站", "新开传奇", "时时彩", "撸撸色", "色中色", "韩国三级电影",
    "在线a视频", "国产模特私拍视频", "av视频", "香港经典三级", "毛片免费观看",
    "伊人大香蕉", "久久网", "日本高清色情", "欧美色图", "亚洲色综合", "伊人香蕉视频",
    "三级在线播放", "青青草在线", "韩国19禁电影", "偷偷鲁手机在线", "一起撸",
    "人人干免费在线视频", "亚洲国产手机在线无码", "欧美三级网站", "五月婷婷",
    "韩国理论片", "福利片_九九", "苍苍影院", "变色桃花源完整版", "亚洲一区",
    "日本一本二本三区无码", "日本一区二区三区", "亚洲人成视频", "免费人成视频",
    "欧美成 人", "男女啪", "久久爱", "免费人成", "天天j", "久久精品视频",
    "国内偷拍在线精品", "亚洲国产在线视频", "在线aV", "自拍偷拍", "国内偷拍",
    "欧美另类", "亚洲色av", "av成人网", "日本av", "欧美av", "成人av", "亚洲av",
    "av在线", "av天堂", "av电影", "av视频", "一级AVA", "免费AV视频", "AV视频",
    "免费黄片", "天天日", "天天啪", "日狠狠", "国产自拍", "深喉", "国产AV",
    "久久偷拍", "一本到2018", "快播成人片", "亚洲欧美国产", "东京热", "另类图片",
    "情色五月天", "色情五月", "伊人在线", "亚洲偷拍", "国产与偷拍", "威尼斯人官网威",
    "日韩无码", "无码中字", "一级毛片", "日本毛片", "亚洲毛片", "久久不射",
    "色姑娘综合网", "天天舔", "天天射", "婷婷我去也", "偷窥女厕所", "免费啪视频",
    "亚洲色欲", "色老头", "妹子自流白浆", "国产午夜精华", "童颜巨乳", "SM重口味",
    "美少女", "在线视频", "欧美极品", "日韩无码", "日韩有码", "极骚萝莉",
    "人妖视频", "强奸乱伦", "视频三区", "绝美少女", "国产精品", "自拍偷拍",
    "萝莉少女", "3P合辑", "视频四区", "自慰喷水", "人妻系列", "巨乳系列",
    "处女专栏", "无码专区", "视频五区", "在线视频", "亚洲电影", "欧美电影",
    "制服丝袜", "强奸乱伦", "变态另类", "经典三级", "成人动漫", "人妻系列",
    "丝袜诱惑", "美臀美颜", "日韩无码", "巨乳诱惑", "颜射口交", "激情图区",
    "亚洲色图", "欧美色图", "乱伦熟女", "自拍偷拍", "美女诱惑", "巨乳诱惑",
    "淫荡人妻", "情色文学", "人妻交换", "家庭乱伦", "在线博彩", "渣女课堂",
    "情趣用品", "备用网址", "吉祥坊", "宝博体育", "下注", "万博体育", "皇冠博彩",
    "澳门威尼斯人", "大撒比", "真人荷官", "体育app", "耀世平台", "平台买球",
    "法轮功", "午夜免费看", "澳门新葡萄娱乐", "博亚体育", "金沙棋牌",
    "男女乱婬真视频", "性欲", "情欲", "性爱", "攻打中国", "1彩3娱乐平台",
    "傲世皇朝注册", "娱乐城代操", "澳门新葡京", "乐鱼", "威尼斯人81818官方网站",
    "押注", "投注", "皇冠正网", "开奖直播现场", "app下载", "澳门尼威斯人网站",
    "爻", "卦相", "算命", "性生活", "体育官网下载app", "葡京娱乐场官网",
    "威尼斯wnsr888", "万搏买球", "亚搏体育", "亚搏全网", "澳博集团平台",
    "影片限制特定使用者", "草莓视频", "乐天堂", "ao3", "bob手机", "特畅网络",
    "太阳娱", "高清免费", "凤凰彩票", "w88", "线上买球", "电竞体育", "一對一",
    "久久中文",
]