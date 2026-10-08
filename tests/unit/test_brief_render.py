import unittest

from lei_signal.portfolio.brief_render import render_brief


class BriefRenderTests(unittest.TestCase):
    def sample(self, slot="1135"):
        return {
            "slot": slot,
            "generated_at": "2026-10-08T11:35:00+08:00",
            "first_observation": False,
            "holdings": [
                {
                    "display_name": "示例基金",
                    "code": "123456",
                    "group_name": "宽基",
                    "holding_as_of": "2026-09-04",
                    "facts": {
                        "nav_value": 1.234,
                        "nav_date": "2026-10-07",
                        "gaps": ["缺少同产品行情"],
                    },
                },
                {
                    "display_name": "名称未知",
                    "code": "654321",
                    "holding_as_of": None,
                    "facts": {"nav_value": None, "nav_date": None, "gaps": []},
                },
            ],
            "changes": [{"display_name": "示例基金", "code": "123456", "fields": ["nav_value"]}],
            "removed_since_previous": [{"display_name": "已移出基金", "code": "111111"}],
            "plan_review": [
                {
                    "display_name": "示例基金",
                    "state": "按系统原计划逐项复核",
                    "gaps": [],
                    "system_alerts": [
                        {
                            "code": "STOP_PRICE_BREACHED",
                            "data_as_of": "2026-10-07",
                            "actionable_from": "2026-10-08",
                            "next_step_cn": "复核原计划",
                        }
                    ],
                }
            ],
            "trade_ledger": {
                "available": True,
                "changes": [
                    {
                        "kind": "new",
                        "record": {
                            "display_name": "示例基金",
                            "side": "buy",
                            "trade_date": "2026-10-06",
                            "price_status": "pending",
                        },
                    }
                ],
                "pending_pricing": ["t1"],
            },
            "blogger_window": {"status": "verified", "date": "2026-10-07"},
            "blogger_previous_trading_day": [
                {
                    "title": "视频标题",
                    "source": "bilibili",
                    "published_at": "2026-10-07T10:00:00+08:00",
                    "content_basis": "仅标题或简介，不能概括完整视频建议",
                }
            ],
            "news": [
                {
                    "title": "市场消息",
                    "source_name": "公开来源",
                    "published_at": "2026-10-08T09:00:00+08:00",
                    "symbols": ["123456"],
                    "summary": "简短背景",
                }
            ],
            "news_coverage": {
                "truncated": True,
                "last_run": {
                    "errors": [{"source": "bilibili", "error": "/private/path/cache.json"}]
                },
            },
            "unqualified_news": [{"id": 1}],
            "source_status": {
                "workspace": {"ok": True},
                "news": {"ok": False, "error": "/private/path/source.json"},
            },
        }

    def test_noon_is_information_only_and_includes_names_and_actual_dates(self):
        report = render_brief(self.sample())
        self.assertIn("本次为信息汇总", report)
        self.assertIn("不给出买卖建议", report)
        self.assertIn("**示例基金**", report)
        self.assertIn("| 名称未知 |", report)
        self.assertIn("2026-10-07", report)
        self.assertIn("关联持仓：**示例基金**", report)
        self.assertIn("公开来源（链接未提供）", report)
        self.assertIn("净值变化", report)
        self.assertNotIn("nav_value", report)
        self.assertIn("发布时间：2026-10-08 09:00 +0800", report)
        self.assertIn("上一个 A 股交易日 2026-10-07", report)
        self.assertIn("可能不完整", report)
        self.assertIn("更新失败", report)
        self.assertNotIn("/private/path", report)
        self.assertNotIn("cache.json", report)

    def test_code_is_not_used_as_a_product_name(self):
        packet = self.sample()
        packet["holdings"][1].pop("display_name")
        packet["holdings"][1]["name"] = "654321"
        report = render_brief(packet)
        self.assertIn("| 名称未知 |", report)

    def test_afternoon_lists_only_packet_plan_review_and_pending_prices(self):
        packet = self.sample("1440")
        report = render_brief(packet)
        self.assertIn("## 原计划复核", report)
        self.assertIn("资料日期：2026-10-07", report)
        self.assertIn("适用日期：2026-10-08", report)
        self.assertIn("另有 1 条记录等待系统净值定价", report)
        self.assertNotIn("STOP_PRICE_BREACHED", report)  # internal rule codes stay out of prose
        self.assertIn("复核原计划", report)  # action wording comes from the qualified server review

    def test_changes_precede_plan_and_trade_sections(self):
        packet = self.sample("1440")
        packet["changes"] = [
            {
                "holding_id": "h1",
                "display_name": "示例基金",
                "code": "123456",
                "fields": ["nav_value"],
            }
        ]
        packet["holdings"][0]["holding_id"] = "h1"
        report = render_brief(packet)
        self.assertLess(report.index("## 本次变化"), report.index("## 原计划复核"))
        self.assertLess(report.index("## 原计划复核"), report.index("## 成交记录"))
        self.assertIn("净值变化（当前净值 1.234）", report)

    def test_ordinary_news_is_limited_and_shows_holding_name_and_source_link(self):
        packet = self.sample()
        packet["news"] = [
            {
                "title": f"普通新闻{i}",
                "source_name": "来源甲",
                "url": "https://news.example/item",
                "published_at": "2026-10-08T09:00:00+08:00",
                "symbols": ["123456"] if i == 1 else None,
            }
            for i in range(10)
        ]
        report = render_brief(packet)
        self.assertIn("普通新闻：共 10 条，以下列出 8 条，省略 2 条。", report)
        self.assertIn("**示例基金**", report)
        self.assertIn("[来源甲](https://news.example/item)", report)
        for i in range(8):
            self.assertIn(f"普通新闻{i}", report)
        self.assertNotIn("普通新闻8（", report)
        self.assertNotIn("普通新闻9（", report)

    def test_background_observations_keep_recorded_values_dates_and_sources(self):
        packet = self.sample()
        packet["market_background"] = {
            "cn": {
                "ok": True,
                "data": {
                    "items": [
                        {
                            "label": "融资余额",
                            "value": 25404.57,
                            "unit": "亿元",
                            "observation_date": "2026-09-30",
                            "source_name": "交易所数据",
                            "source_url": "https://data.example/item",
                            "quality_status": "time_unverified",
                            "quality_reason": "发布时间尚未核实",
                        }
                    ]
                },
            },
            "us": {
                "ok": True,
                "data": {
                    "items": [
                        {
                            "label": "VIX",
                            "value": 15.08,
                            "unit": "指数点",
                            "observation_date": "2026-10-07",
                            "source_name": "公开来源",
                        }
                    ]
                },
            },
        }
        report = render_brief(packet)
        self.assertIn("融资余额：25404.57亿元（资料日期：2026-09-30", report)
        self.assertIn("[交易所数据](https://data.example/item)", report)
        self.assertIn("发布时间尚未核实", report)
        self.assertIn("VIX：15.08指数点（资料日期：2026-10-07", report)
        self.assertNotIn("因此市场看涨", report)

    def test_pending_gaps_are_aggregated_and_holdings_table_is_collapsible(self):
        packet = self.sample("1440")
        packet["holdings"] = [
            {
                "holding_id": f"h{i}",
                "display_name": f"基金{i}",
                "code": f"10000{i}",
                "holding_as_of": "2026-10-07",
                "facts": {
                    "nav_value": 1.2,
                    "nav_date": "2026-10-07",
                    "gaps": ["缺少同一产品行情", "尚未关联有效计划"],
                },
            }
            for i in range(29)
        ]
        packet["plan_review"] = [
            {
                "holding_id": f"h{i}",
                "display_name": f"基金{i}",
                "state": "原计划或可用行情不足，不能判定安全或失效",
                "gaps": ["缺少同一产品行情", "尚未关联有效计划"],
            }
            for i in range(29)
        ]
        report = render_brief(packet)
        self.assertEqual(report.count("缺少同一产品行情（29只）"), 1)
        self.assertEqual(report.count("尚未关联有效计划（29只）"), 1)
        self.assertIn("<details><summary>持仓明细（29只）</summary>", report)
        table_rows = [line for line in report.splitlines() if line.startswith("| 基金")]
        self.assertEqual(len(table_rows), 29)
        self.assertNotIn("待补资料：缺少同一产品行情", report)

    def test_priced_means_system_nav_pricing_not_platform_confirmation(self):
        packet = self.sample("1440")
        packet["trade_ledger"]["changes"][0]["record"].update(
            price_status="priced", priced_nav=1.234, trade_date="2026-10-06"
        )
        report = render_brief(packet)
        self.assertIn("系统已按净值定价 1.234", report)
        self.assertIn("平台成交确认需另行核对", report)

    def test_blogger_items_show_titles_without_summaries(self):
        packet = self.sample()
        packet["blogger_previous_trading_day"][0]["summary"] = "一段概括出的交易建议"
        report = render_brief(packet)
        self.assertIn("视频标题", report)
        self.assertIn("只有标题时不概括完整建议", report)
        self.assertNotIn("一段概括出的交易建议", report)

    def test_audio_basis_and_timestamp_are_visible_but_model_summary_is_not_assumed(self):
        packet = self.sample()
        packet["blogger_previous_trading_day"][0].update(
            content="公开音频中的原话",
            summary="未经验证的买卖建议",
            video_content={
                "coverage": {"fraction": 0.91},
                "segments": [{"start": 64.0, "end": 70.0, "text": "公开音频中的原话"}],
            },
        )
        report = render_brief(packet)
        self.assertIn("本机语音转写，未人工校正", report)
        self.assertIn("91.0%", report)
        self.assertIn("01:04", report)
        self.assertIn("公开音频中的原话", report)
        self.assertNotIn("未经验证的买卖建议", report)

    def test_video_failure_preserves_named_title_and_reports_missing_content(self):
        packet = self.sample()
        packet["video_content_coverage"] = {"errors": [{"reason": "audio unavailable"}]}
        report = render_brief(packet)
        self.assertIn("视频标题", report)
        self.assertIn("未读到完整视频内容", report)
        self.assertIn("视频内容读取有 1 项待核", report)


if __name__ == "__main__":
    unittest.main()
