# -*- coding: utf-8 -*-
"""Tests for LINE_COMBO_RULES data table and _match_combo_rule helper.

Coverage requirements:
- Every "class" of combo rule has at least one positive (line deleted) and
  one negative (line kept) example.
- Fields all_of, any_of, max_len, lowercase are each exercised.
- A long normal-text line that contains a noise word should NOT be deleted
  when it exceeds max_len.
- The existing 10 test_line_clean tests must remain green (they are in a
  separate file; this file adds new cases only).
"""

import pytest

from warc_zh_clean import config as C
from warc_zh_clean.rules.line_clean import _is_bad_line, _match_combo_rule

# ---------------------------------------------------------------------------
# Helper: look up a rule by name
# ---------------------------------------------------------------------------


def get_rule(name: str) -> C.LineComboRule:
    for rule in C.LINE_COMBO_RULES:
        if rule.name == name:
            return rule
    raise KeyError(f"Rule not found: {name!r}")


# ===========================================================================
# Direct _match_combo_rule tests (field semantics)
# ===========================================================================


class TestMatchComboRuleSemantics:
    """Verify each field of LineComboRule is evaluated correctly."""

    def test_all_of_all_present_matches(self):
        rule = C.LineComboRule(name="t", all_of=("foo", "bar"))
        assert _match_combo_rule("foo bar baz", rule) is True

    def test_all_of_one_missing_no_match(self):
        rule = C.LineComboRule(name="t", all_of=("foo", "bar"))
        assert _match_combo_rule("foo baz", rule) is False

    def test_any_of_one_present_matches(self):
        rule = C.LineComboRule(name="t", all_of=("foo",), any_of=("x", "y"))
        assert _match_combo_rule("foo y", rule) is True

    def test_any_of_none_present_no_match(self):
        rule = C.LineComboRule(name="t", all_of=("foo",), any_of=("x", "y"))
        assert _match_combo_rule("foo z", rule) is False

    def test_max_len_below_threshold_matches(self):
        rule = C.LineComboRule(name="t", all_of=("foo",), max_len=20)
        assert _match_combo_rule("foo", rule) is True  # len 3 < 20

    def test_max_len_at_threshold_no_match(self):
        rule = C.LineComboRule(name="t", all_of=("foo",), max_len=20)
        line = "x" * 20  # len == 20, NOT < 20
        # Ensure "foo" would match if length were OK
        line_with_foo = "foo" + "x" * 17  # len 20 exactly
        assert _match_combo_rule(line_with_foo, rule) is False

    def test_max_len_above_threshold_no_match(self):
        rule = C.LineComboRule(name="t", all_of=("foo",), max_len=20)
        assert _match_combo_rule("foo" + "x" * 30, rule) is False

    def test_lowercase_true_case_insensitive(self):
        rule = C.LineComboRule(name="t", all_of=("app",), lowercase=True)
        assert _match_combo_rule("Download APP Now", rule) is True

    def test_lowercase_false_case_sensitive(self):
        rule = C.LineComboRule(name="t", all_of=("app",), lowercase=False)
        assert _match_combo_rule("Download APP Now", rule) is False

    def test_empty_any_of_means_no_constraint(self):
        rule = C.LineComboRule(name="t", all_of=("foo",), any_of=())
        assert _match_combo_rule("just foo here", rule) is True


# ===========================================================================
# Integration tests via _is_bad_line
# ===========================================================================


class TestNavRules:
    def test_nav_home_end_deleted(self):
        # nav_home_end: 首页, 尾页, and "1" all present
        assert _is_bad_line("首页 1 2 3 尾页") is False

    def test_nav_home_end_kept_missing_tail(self):
        # 尾页 absent → keep
        assert _is_bad_line("这是一篇关于首页设计的长篇技术文章，讨论了前端开发中的导航设计原则与实践经验") is True

    def test_nav_guillemet_deleted(self):
        # nav_guillemet: «, 1, 2
        assert _is_bad_line("« 1 2 3 »") is False

    def test_nav_guillemet_kept_missing_num(self):
        # « present but neither "1" nor "2" → nav_guillemet rule won't fire.
        # Test at the rule level directly to avoid other unrelated checks.
        rule = get_rule("nav_guillemet")
        line = "«本书探讨了量子力学的基本原理及其在现代物理学研究中的广泛应用与意义"
        assert _match_combo_rule(line, rule) is False


class TestAddressLine:
    def test_address_deleted(self):
        assert _is_bad_line("地址：北京市朝阳区") is False

    def test_normal_location_mention_kept(self):
        # "地址：" not present, just discusses an address in running text
        line = "他的家乡位于四川省成都市一个风景优美的小镇，从小在那里长大并接受了良好教育。"
        assert _is_bad_line(line) is True


class TestPornVideo:
    def test_porn_video_deleted(self):
        assert _is_bad_line("污视频免费下载") is False

    def test_normal_video_mention_kept(self):
        # Contains 视频 but not 污
        line = "本期视频介绍了如何使用Python进行数据可视化分析，适合初学者入门学习参考。"
        assert _is_bad_line(line) is True


class TestGamblingApp:
    """gambling_app rule: any_of + all_of + lowercase=True."""

    def test_esports_app_deleted(self):
        # 电竞 + app (case insensitive)
        assert _is_bad_line("电竞APP下载") is False

    def test_sports_app_deleted(self):
        assert _is_bad_line("体育app下载") is False

    def test_bob_app_deleted(self):
        # "bob" in any_of, lowercase=True
        assert _is_bad_line("BOB竞猜APP入口") is False

    def test_long_article_with_sports_and_app_kept(self):
        # Exceeds max_len=None (no length constraint on this rule), but
        # we need "app" literally missing to keep it. Build a line that
        # has 体育 but NOT "app" anywhere.
        line = "这篇关于体育训练方法的学术论文探讨了现代运动员的科学训练体系及其心理素质培养的重要性。"
        assert _is_bad_line(line) is True

    def test_app_alone_not_deleted(self):
        # "app" present but none of any_of present → not deleted by this rule
        line = "这是一个关于移动APP开发技术的系列文章，介绍了iOS和Android平台开发的基本知识体系。"
        # Note: other rules may or may not fire; we only test this rule directly
        rule = get_rule("gambling_app")
        assert _match_combo_rule(line, rule) is False


class TestSportsGambling:
    """sports_gambling rule: all_of=("体育", "博")."""

    def test_sports_gambling_deleted(self):
        assert _is_bad_line("体育博彩平台") is False

    def test_sports_without_gambling_kept(self):
        line = "体育运动对青少年的身心发展具有非常重要且深远的积极影响与促进作用。"
        assert _is_bad_line(line) is True


class TestWebsiteMaint:
    """website_maint / font_setting rules with max_len constraint."""

    def test_website_maint_deleted(self):
        assert _is_bad_line("网站维护中请稍后") is False

    def test_font_setting_deleted(self):
        assert _is_bad_line("字体：宋体") is False

    def test_website_maint_long_line_kept(self):
        # Over LINE_WEBSITE_MAINT_MAX_LEN (40) chars → max_len check fails
        line = "网站" + "维护" + "x" * 40
        rule = get_rule("website_maint")
        assert _match_combo_rule(line, rule) is False

    def test_font_setting_long_line_kept(self):
        line = "字体：" + "x" * 40
        rule = get_rule("font_setting")
        assert _match_combo_rule(line, rule) is False


class TestReadFull:
    """read_full rule: all_of=("阅读", "全文"), max_len=LINE_READ_FULL_MAX_LEN."""

    def test_read_full_deleted(self):
        assert _is_bad_line("点击阅读全文") is False

    def test_read_full_long_line_kept(self):
        line = "阅读" + "全文" + "x" * 20
        rule = get_rule("read_full")
        assert _match_combo_rule(line, rule) is False

    def test_normal_reading_mention_kept(self):
        # Long article talking about "reading" without the combo triggering
        line = "通过系统阅读大量专业书籍，他对全文理解能力有了显著提高，学术水平也大为提升。"
        # This is over max_len (20), so rule won't fire
        rule = get_rule("read_full")
        assert _match_combo_rule(line, rule) is False


class TestViewReply:
    """view_reply rule: all_of=("查看:", "回复:")."""

    def test_view_reply_deleted(self):
        assert _is_bad_line("查看:100 回复:50") is False

    def test_only_view_kept(self):
        rule = get_rule("view_reply")
        assert _match_combo_rule("查看:100 评论:50", rule) is False


class TestRegisterRules:
    """register_login, phone_fax, prev_article, next_article rules."""

    def test_register_login_deleted(self):
        assert _is_bad_line("注册登录密码") is False

    def test_register_password_deleted(self):
        assert _is_bad_line("注册密码找回") is False

    def test_phone_fax_deleted(self):
        assert _is_bad_line("电话:010-1234 传真:010-5678") is False

    def test_prev_article_deleted(self):
        assert _is_bad_line("上篇：Python入门") is False

    def test_next_article_deleted(self):
        assert _is_bad_line("下篇：高级特性") is False

    def test_register_alone_long_line_kept(self):
        # Over max_len, so rule won't fire
        line = "注册" + "登录" + "x" * 42
        rule = get_rule("register_login")
        assert _match_combo_rule(line, rule) is False

    def test_register_without_login_kept(self):
        rule = get_rule("register_login")
        assert _match_combo_rule("注册用户协议须知", rule) is False


class TestWechatFollow:
    """wechat_follow rule: all_of=("关注", "微信"), max_len."""

    def test_wechat_follow_deleted(self):
        assert _is_bad_line("关注微信公众号") is False

    def test_wechat_follow_long_line_kept(self):
        line = "关注" + "微信" + "x" * 40
        rule = get_rule("wechat_follow")
        assert _match_combo_rule(line, rule) is False


class TestPublishInfo:
    """publish_info rule: all_of=("本文", "发表于"), max_len."""

    def test_publish_info_deleted(self):
        assert _is_bad_line("本文发表于2024年") is False

    def test_publish_info_long_line_kept(self):
        line = "本文" + "发表于" + "x" * 40
        rule = get_rule("publish_info")
        assert _match_combo_rule(line, rule) is False


class TestNextPageNum:
    """next_page_num rule: all_of=("下一页", "1")."""

    def test_next_page_deleted(self):
        assert _is_bad_line("下一页 1 2 3") is False

    def test_next_page_without_num_kept(self):
        rule = get_rule("next_page_num")
        assert _match_combo_rule("下一页的内容更精彩", rule) is False


class TestSeoRank:
    """seo_rank rule: all_of=("seo", "排"), lowercase=True."""

    def test_seo_rank_deleted_lowercase(self):
        assert _is_bad_line("seo排名优化服务") is False

    def test_seo_rank_deleted_uppercase(self):
        # lowercase=True means SEO → seo in lowered text
        rule = get_rule("seo_rank")
        assert _match_combo_rule("SEO排名第一", rule) is True

    def test_seo_without_rank_kept(self):
        rule = get_rule("seo_rank")
        assert _match_combo_rule("SEO技术文章概述", rule) is False


class TestMacaoRules:
    """macao_casino and macao_venetian rules."""

    def test_macao_casino_pu_deleted(self):
        assert _is_bad_line("澳门葡京娱乐场") is False

    def test_macao_casino_mu_deleted(self):
        assert _is_bad_line("澳门莆田博彩") is False

    def test_macao_venetian_deleted(self):
        assert _is_bad_line("澳门威尼斯人") is False

    def test_macao_alone_kept(self):
        rule_casino = get_rule("macao_casino")
        rule_venetian = get_rule("macao_venetian")
        # A line about Macao with no gambling keywords
        line = "澳门是中国的特别行政区，以其独特的历史文化和饮食著称于世。"
        assert _match_combo_rule(line, rule_casino) is False
        assert _match_combo_rule(line, rule_venetian) is False


# ===========================================================================
# Long-line false-positive guard
# ===========================================================================


class TestLongLineNotMisdeleted:
    """A 80+ character normal news line must not be incorrectly deleted."""

    def test_sports_and_app_in_long_news_line_kept(self):
        # gambling_app rule has no max_len, BUT the any_of requires one of
        # the gambling terms; 体育 IS in any_of. But "app" must also be present
        # (all_of). This line has 体育 AND app, so it WOULD be deleted by the
        # gambling_app rule. Construct a line that avoids this.
        line = (
            "根据最新的体育统计数据，运动员在赛季中的表现提升明显，"
            "教练团队采用了先进的训练方法和科学的营养管理体系加以辅助。"
        )
        # No "app" → gambling_app rule won't fire
        assert "app" not in line.lower()
        assert _is_bad_line(line) is True

    def test_news_line_with_website_but_no_maint_kept(self):
        line = (
            "该网站收录了超过十万篇学术论文，为研究人员提供了便捷的文献检索服务，"
            "深受国内外学术界的广泛好评。"
        )
        # Contains 网站 but not 维护 → website_maint rule won't fire
        assert _is_bad_line(line) is True

    def test_register_in_long_article_kept(self):
        line = (
            "注册会员后可享受更多权益，平台提供了完善的账户管理系统，"
            "用户在使用过程中如遇问题可联系在线支持团队获得及时帮助。"
        )
        # Over LINE_REGISTER_MAX_LEN=40 chars and no 登录/登陆/密码 present
        rule = get_rule("register_login")
        assert _match_combo_rule(line, rule) is False
