# -*- coding: utf-8 -*-
"""LineCleanRule: line-level noise deletion + head/tail trimming.

Merges logic from ``core/line_rules.py``.
This is a *transform* rule — it never rejects, only mutates ``ctx.text``.
"""

import re

from warc_zh_clean import config as C
from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.base import BaseRule


# ---------------------------------------------------------------------------
# Pure helper functions (no ctx dependency)
# ---------------------------------------------------------------------------


def _is_bad_line2(text: str) -> bool:
    """Check if a line is a bad line (figure, page number, symbol line).

    Returns True if the line is acceptable, False if it should be removed.
    """
    if re.search(
        r"\图\d/\d+/\d+|←.*?→|\图\d/\d+|\图\d|\第\d+页|\共\d+页", text
    ) or re.search(r"↓↓|Read more|详情>>", text):
        return False
    if re.search(r"■|»|◆|▲|★|●|▼|♦|♥|⚡|↘|▶|👇|※|▋|Ø", text):
        return False
    if re.search(
        r"查看详情|P\d+|查看全文>>|阅读全文>>|more>>|图为：|返回搜狐，查看更多"
        r"|查看更多>>|\|站点地图|《查看更多》|\?\?|\（图中左起.{1,600}）"
        r"|>>>点此进入怀旧频道",
        text,
    ):
        return False
    if re.search(
        r".*\d+月\d+日+(消息|讯)+（.{2,100}）|.*\d+月\d+日+(消息|讯)", text
    ) or re.search(r"\d+月\d+日(消息|讯)", text):
        return False
    return True


def _is_bad_line(line: str) -> bool:
    """Main line-level bad line detector.

    Returns True if the line should be kept, False if it should be removed.
    """
    if line.strip() == "":
        return True

    zh_chars = re.findall("[\u4e00-\u9fff]", line)
    en_chars = re.findall(r"[A-Za-z\s]", line)

    # Contact info in short lines
    bad_words = 0
    if len(line) < C.LINE_CONTACT_INFO_MAX_LEN:
        cleaned = line.replace(" ", "").replace("\xa0", "").replace("\n", "")
        for t in C.LINE_CONTACT_KEYWORDS:
            if t in cleaned:
                bad_words += 1
    if bad_words > C.LINE_CONTACT_KEYWORD_MIN_HITS:
        return False

    # Short line ending with colon
    if (
        len(re.sub("\\s", "", line)) <= C.LINE_COLON_END_MAX_LEN
        and line.strip().endswith("：")
        and len(re.findall("说|道|一|二|三|四|五|六|七|八|九|十|[0-9]|、|\\.", line)) == 0
    ):
        return False

    # Noise word patterns
    if (
        re.findall(C.dummy_words_rules, line.lower())
        or re.findall(C.dummy_words_rules, line.replace(" ", "").replace("\xa0", "").lower())
        or re.findall(C.end_prompts, line.replace(" ", ""))
    ):
        return False

    # Bracket-heavy short lines
    if len(line.replace("】", "").replace("【", "").replace(" ", "").replace("\n", "")) <= C.LINE_BRACKET_MAX_LEN:
        if line.count("【") >= 2:
            return False

    # Very short pure CJK lines
    if len(zh_chars) == len(line) and len(line) <= C.LINE_SHORT_ZH_MAX_LEN:
        return False

    # Very short pure English lines
    if len(en_chars) == len(line) and len(line) <= C.LINE_SHORT_EN_MAX_LEN and len(line.split()) <= C.LINE_SHORT_EN_MAX_WORDS:
        return False

    # Navigation patterns
    if "首页" in line and "尾页" in line and "1" in line:
        return False
    if "\u00ab" in line and "1" in line and "2" in line:
        return False
    if "地址：" in line:
        return False
    if line.endswith("上一篇") or line.endswith("下一篇"):
        return False
    if line.count("Q微") > 2:
        return False

    # Keyword check for short lines
    if len(line.replace(" ", "")) <= C.LINE_KEYWORD_CHECK_MAX_LEN:
        if len(line) <= C.LINE_BULLET_MAX_LEN and line.startswith("•"):
            return False
        if len(
            re.findall(
                r"APP|网址：|首页|分钟前|联系：|联系人：|app|安卓手机|手机版"
                r"|翻译：|编辑：|校对：|审核：|Source:|发E\-mail|相关新闻"
                r"|\d+人在|篇文章|二维码|喜欢|收藏|来自：|意见反馈|机床铸件"
                r"|客服|敬请期待|编辑：|<URL>|SEE MORE|扫一扫|扫码关注"
                r"|您现在|评论|下一页|联系我们|请输入计算结果|上一页|下载|QQ"
                r"|评论列表|站长|\d+次访问|安卓版下载|手机版下载|浏览：\d+"
                r"|全部\d+个答案|\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|\d{4}-\d{2}",
                line,
            )
        ) > 0 or len(re.findall(C.end_prompts, line)) > 0:
            return False

    # Detail/more patterns at line edges
    if (
        "详情" in line[-10:]
        or "更多" in line[-10:]
        or "大小" in line[:10]
        or line.count("本站") >= 2
        or "浏览次数：" in line
        or "点击次数：" in line
    ):
        return False

    # Porn video pattern
    if "污" in line and "视频" in line:
        return False

    # Porn/gambling keywords with app
    if (
        "电竞" in line
        or "体育" in line
        or "博" in line
        or "彩" in line
        or "大片" in line
        or "竞猜" in line
        or "bob" in line.lower()
        or "18禁" in line
        or "直播" in line
        or "传媒" in line
        or "真人" in line
        or "赚钱" in line
        or "无码" in line
        or "影视" in line
        or "高清" in line
        or "提现" in line
    ) and "app" in line.lower():
        return False

    if "体育" in line and "博" in line:
        return False

    # Website maintenance / font
    if (("网站" in line and "维护" in line) or "字体：" in line) and len(line) < C.LINE_WEBSITE_MAINT_MAX_LEN:
        return False

    # Read full text
    if "阅读" in line and "全文" in line and len(line) < C.LINE_READ_FULL_MAX_LEN:
        return False

    # View/reply pattern
    if "查看:" in line and "回复:" in line:
        return False

    # Register/login pattern
    if (
        ("注册" in line and ("登录" in line or "登陆" in line or "密码" in line))
        or ("电话" in line and "传真" in line)
        or "上篇：" in line
        or "下篇：" in line
    ) and len(line) < C.LINE_REGISTER_MAX_LEN:
        return False

    # WeChat follow
    if "关注" in line and "微信" in line and len(line) < C.LINE_WECHAT_FOLLOW_MAX_LEN:
        return False

    # Publish info
    if "本文" in line and "发表于" in line and len(line) < C.LINE_PUBLISH_INFO_MAX_LEN:
        return False

    # Next page
    if "下一页" in line and "1" in line:
        return False

    # SEO
    if "seo" in line.lower() and "排" in line:
        return False

    # Macao gambling
    if "澳门" in line and ("葡" in line or "莆" in line):
        return False
    if "澳门" in line and "威" in line and "尼" in line:
        return False

    # Very short lines
    if len(line) <= C.LINE_VERY_SHORT_MAX_LEN and "|" not in line and "&" not in line:
        return False

    if line.isdigit():
        return False

    # Parenthesized numbers
    if len(re.findall(r"\(\d+\)", line)) >= C.LINE_PAREN_NUM_MIN:
        return False

    # Datetime ratio in line
    if len("".join(re.findall(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", line))) > len(line) * C.LINE_DATETIME_RATIO:
        return False

    # JSON-like / quote patterns
    if ("}" in line and ":" in line and "." in line) or line.count('"') >= C.LINE_QUOTE_MIN or line.count(">") >= C.LINE_GT_MIN:
        return False

    # HTML tags
    if "</" in line:
        return False

    # Single-char or separator lines
    if "/" == line or "," == line or "x" == line or "=======" in line:
        return False

    # Previous/next article after stripping
    temp = line.strip().strip("•").strip().replace("【", "").replace("（", "").replace("(", "")
    if (
        temp.startswith("下一篇")
        or temp.endswith("下一篇")
        or temp.startswith("上一篇")
        or temp.startswith("作者：")
        or temp.startswith("作者:")
    ):
        return False

    if "在线客服" in temp:
        return False

    # Bad line 2 check
    if not _is_bad_line2(line):
        return False

    return True


def _line_deleting_end(lines: list[str]) -> list[str]:
    """Remove bad lines from the end section of text."""

    def is_bad(text: str) -> bool:
        if len(re.findall(C.TAIL_BAD_KEYWORDS, text)) > 0:
            return False
        if text.count("|") >= C.LINE_PIPE_MIN:
            return False
        if text.count("]") >= 2 and text.count("[") >= 2:
            return False
        if text.count("】") >= C.LINE_BRACKET_DENSE_BRACKET and text.count("【") >= C.LINE_BRACKET_DENSE_BRACKET:
            return False
        return True

    return list(filter(lambda x: is_bad(x), lines))


def _line_deleting_head(lines: list[str]) -> list[str]:
    """Remove bad lines from the head section of text."""

    def is_bad(text: str) -> bool:
        if len(re.findall(C.HEAD_BAD_KEYWORDS, text)) > 0:
            return False
        return True

    return list(filter(lambda x: is_bad(x), lines))


def _line_deleting(text: str) -> str:
    """Apply line-level deletion rules.

    Args:
        text: Input text with newline-separated lines.

    Returns:
        Text with bad lines removed and cleanup applied.
    """
    lines = text.split("\n")

    res = list(filter(lambda x: _is_bad_line(x), lines))

    # Last line cleanup
    if len(res) > 0:
        last_line = res[-1]
        last_line_no_zh = len(re.findall("[\u4e00-\u9fff]", last_line)) == 0
        if (
            (last_line_no_zh and len(last_line.strip()) <= C.LINE_TAIL_LAST_LINE_MAX_LEN)
            or "Copyright".lower() in last_line.lower()
            or len(re.findall(C.TAIL_LAST_LINE_PATTERNS, last_line)) > 0
        ):
            res = res[:-1]

    # First line cleanup
    if len(res) > 0:
        if "菜单" in res[0] or "首页" in res[0] or ">" in res[0]:
            res = res[1:]

    # Find first markdown heading
    has_title = False
    first_title = 0
    for cnt1, t in enumerate(res):
        if t.strip().startswith("#"):
            has_title = True
            first_title = cnt1
            break
    if has_title:
        res = res[first_title:]

    new_lines = res

    # Head/tail trimming
    if len(new_lines) > 3:
        new_lines_head = _line_deleting_head(new_lines[:3])
        new_lines = new_lines_head + new_lines[3:]
    if len(new_lines) >= 3:
        new_lines_end = _line_deleting_end(new_lines[-3:])
        new_lines = new_lines[:-3] + new_lines_end

    final_res = (
        "\n".join(new_lines)
        .replace(r"<\/p>", "\n")
        .replace("\u3000\u3000", "\n\n")
        .replace("\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
        .strip()
    )
    final_res = C.SPACES_4_RE.sub("    ", final_res).replace("\\$", "$").replace("\ufeff ", "").replace("``````", "```")

    return final_res


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class LineCleanRule(BaseRule):
    """Line-level noise deletion rule.

    Removes bad lines, trims head/tail sections, and applies text cleanup.
    This rule never rejects — it only mutates ``ctx.text``.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        text_before = ctx.text
        ctx.text = _line_deleting(ctx.text)
        ctx.text_removed = len(text_before) - len(ctx.text)
        ctx.text_removed_none = len(ctx.text.strip()) == 0
        return ctx