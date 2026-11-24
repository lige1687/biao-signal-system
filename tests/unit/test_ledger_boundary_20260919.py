"""台账边界回归测试（J3，2026-09-19 架构三单之收官单）。

覆盖四层：
- G1 trade_plans schema 边界：计划台账刻意不含数量/金额（migration 010 起的
  账本边界）；状态推进（armed→entered→exited）只动状态机与日期列，
  不偷偷写执行事实（成交价/数量/金额）。
- G2 fund_trades 防重复导入：同一请求身份（request_id）第二次导入
  不新增事实（migration 031 请求身份列回归）。
- G3-A 关联完整性·现状证据层：合法 plan_id 可关联读取；无 plan_id
  允许落库——无计划成交是事实，必须可入账，这是合规设计不是缺陷。
- G3-B 关联完整性·缺口暴露层（xfail）：无效 plan_id（不存在/标的不符/
  方向不符）应被拒绝——这是未来期望。当前生产代码不做校验，
  这些 xfail 是已知生产缺口（2026-09-19 架构评审），不是测试失败；
  一旦补上校验，xfail 会转 XPASS 提醒移除标记。

全部用 tmp 库 + 真实迁移 + 真实写入路径（trades.create_trade /
plans.store），无 mock repository/storage，不触碰生产数据库。
"""
from __future__ import annotations

import pytest

from lei_signal.copilot import trades
from lei_signal.plans import store as plans
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "ledger_boundary.db"))
    yield c
    c.close()


# 计划台账不允许出现的「执行事实」类列名（数量/金额/成交价/账户）。
# 边界口径：trade_plans 只记状态机 + 价位（参考价/失效价/目标价），
# 价位是计划的一部分；执行事实只进 fund_trades。
_EXECUTION_FACT_COLUMNS = {
    "quantity", "qty", "size", "shares",
    "amount", "notional", "value",
    "executed_price", "filled_price", "fill_price", "avg_price", "trade_price",
    "account", "account_id", "broker", "broker_id",
}


def _columns(conn, table: str) -> set[str]:
    return {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _full_plan_kwargs(**over) -> dict:
    """可直接 confirm 到 armed 的完整计划参数。"""
    base = dict(
        symbol="510300",
        module="A",
        direction="long",
        ruleset_version="rules.v1-test",
        reason="回测边界测试计划",
        valid_until="2026-12-31",
        invalidation_price=3.50,
        entry_price_ref=4.00,
        thesis_cn="测试论点",
        invalidation_criteria_cn="跌破失效价",
        drawdown_playbook_cn="减仓",
        take_profit_plan_cn="涨到目标价",
        stop_plan_cn="破位止损",
    )
    base.update(over)
    return base


def _trade_kwargs(**over) -> dict:
    base = dict(
        fund_code="510300",
        fund_name="沪深300ETF",
        side="buy",
        amount=10000.0,
        trade_date="2026-09-18",
    )
    base.update(over)
    return base


def _armed_plan(conn) -> str:
    plan = plans.create_plan(conn, **_full_plan_kwargs())
    plans.confirm_plan(conn, plan.plan_id)
    return plan.plan_id


# ---------------------------------------------------------------- G1

class TestTradePlansSchemaBoundary:
    def test_no_execution_fact_columns(self, conn):
        """schema 边界本身：计划表不存在任何数量/金额/成交价/账户列。"""
        cols = _columns(conn, "trade_plans")
        leaked = cols & _EXECUTION_FACT_COLUMNS
        assert not leaked, f"trade_plans 出现执行事实列: {leaked}"

    def test_state_columns_are_plan_scoped(self, conn):
        """不从「没有字段」推断全部安全：显式断言状态推进相关列是
        状态机 + 日期（entered_on/exited_on/superseded_by），不出现
        执行口径字段；价位列（entry_price_ref/invalidation_price 等）
        是计划价位而非成交事实。"""
        cols = _columns(conn, "trade_plans")
        for required in ("state", "entered_on", "exited_on", "superseded_by",
                         "entry_price_ref", "invalidation_price"):
            assert required in cols
        assert not (cols & _EXECUTION_FACT_COLUMNS)

    def test_state_transitions_do_not_write_execution_facts(self, conn):
        """armed→entered→exited 推进前后逐列 diff：只允许
        state/entered_on/exited_on/updated_at 变化，其余列（含计划价位）
        必须逐字节不变——状态推进不偷偷写执行事实。"""
        plan_id = _armed_plan(conn)

        def row() -> dict:
            r = conn.execute(
                "SELECT * FROM trade_plans WHERE plan_id = ?", (plan_id,)
            ).fetchone()
            return {k: r[k] for k in r.keys()}

        before_armed = row()
        plans.set_entered(conn, plan_id, entered_on="2026-09-18")
        after_entered = row()
        changed_entered = {
            k for k in before_armed if before_armed[k] != after_entered[k]
        }
        assert changed_entered <= {"state", "entered_on", "updated_at"}, (
            f"入场推进改动了计划字段: {changed_entered}"
        )
        assert after_entered["state"] == "entered"
        assert after_entered["entered_on"] == "2026-09-18"
        # entered_on 只记日期，不是成交价/数量
        assert not (changed_entered & _EXECUTION_FACT_COLUMNS)

        plans.set_exited(conn, plan_id, exited_on="2026-09-20")
        after_exited = row()
        changed_exited = {
            k for k in after_entered if after_entered[k] != after_exited[k]
        }
        assert changed_exited <= {"state", "exited_on", "updated_at"}, (
            f"退出推进改动了计划字段: {changed_exited}"
        )
        assert after_exited["state"] == "exited"
        assert after_exited["exited_on"] == "2026-09-20"

    def test_full_state_path_stays_within_plan_boundary(self, conn):
        """整条 draft→armed→entered→exited 走完后，计划行中仍没有任何
        执行事实：所有非空数值列都是计划价位，无数量/金额语义。"""
        plan_id = _armed_plan(conn)
        plans.set_entered(conn, plan_id, entered_on="2026-09-18")
        plans.set_exited(conn, plan_id, exited_on="2026-09-20")
        cols = _columns(conn, "trade_plans")
        assert not (cols & _EXECUTION_FACT_COLUMNS)


# ---------------------------------------------------------------- G2

class TestFundTradesRequestIdentity:
    def test_same_request_id_second_import_no_new_fact(self, conn):
        """同一确认身份（request_id）第二次导入：返回原笔、库里只有一笔。"""
        first = trades.create_trade(
            conn, request_id="req-j3-001", **_trade_kwargs()
        )
        conn.commit()
        second = trades.create_trade(
            conn, request_id="req-j3-001", **_trade_kwargs()
        )
        conn.commit()
        assert first.trade_id == second.trade_id
        n = conn.execute("SELECT COUNT(*) c FROM fund_trades").fetchone()["c"]
        assert n == 1

    def test_same_request_id_no_silent_extra_rows_even_pre_commit(self, conn):
        """不 commit 的连续两次调用也不新增事实（重试/连点场景）。"""
        trades.create_trade(conn, request_id="req-j3-002", **_trade_kwargs())
        trades.create_trade(conn, request_id="req-j3-002", **_trade_kwargs())
        conn.commit()
        n = conn.execute("SELECT COUNT(*) c FROM fund_trades").fetchone()["c"]
        assert n == 1


# ---------------------------------------------------------------- G3-A 现状证据层（必须 PASS）

class TestFundTradesPlanLinkCurrentBehavior:
    def test_valid_plan_id_links_and_reads_back(self, conn):
        """合法 plan_id：成交落库后可经真实读取路径关联到计划。"""
        plan_id = _armed_plan(conn)
        dto = trades.create_trade(
            conn, request_id="req-j3-101",
            plan_id=plan_id, **_trade_kwargs()
        )
        conn.commit()
        assert dto.plan_id == plan_id
        linked = conn.execute(
            "SELECT p.plan_id, p.symbol, p.state, t.trade_id, t.fund_code "
            "FROM fund_trades t JOIN trade_plans p ON p.plan_id = t.plan_id "
            "WHERE t.trade_id = ?",
            (dto.trade_id,),
        ).fetchone()
        assert linked is not None
        assert linked["plan_id"] == plan_id
        assert linked["symbol"] == linked["fund_code"] == "510300"
        assert linked["state"] == "armed"

    def test_missing_plan_id_allowed_current_behavior(self, conn):
        """无 plan_id 成交允许落库（现状记录）：无计划的成交也是事实，
        必须可入账——这是合规设计，不是缺陷。"""
        dto = trades.create_trade(
            conn, request_id="req-j3-102", **_trade_kwargs()
        )
        conn.commit()
        assert dto.plan_id is None
        n = conn.execute(
            "SELECT COUNT(*) c FROM fund_trades WHERE plan_id IS NULL"
        ).fetchone()["c"]
        assert n == 1


# ---------------------------------------------------------------- G3-B 缺口暴露层（xfail）

@pytest.mark.xfail(
    reason="已知生产缺口：plan_id 落库无存在性/标的一致/方向一致校验，"
           "见 2026-09-19 架构评审。这是已知缺口不是测试失败；"
           "补上校验后本测试应转 XPASS 并移除 xfail 标记。",
    strict=True,
)
class TestFundTradesInvalidPlanIdShouldBeRejected:
    """未来期望（当前必然失败，xfail 表达已知缝隙）：
    无效 plan_id 不应静默落库。这是已知生产缺口，不是测试失败。"""

    def test_nonexistent_plan_id_should_be_rejected(self, conn):
        dto = trades.create_trade(
            conn, request_id="req-j3-201",
            plan_id="plan_510300_20990101_deadbeef",  # 不存在
            **_trade_kwargs(),
        )
        conn.commit()
        n = conn.execute(
            "SELECT COUNT(*) c FROM fund_trades t "
            "LEFT JOIN trade_plans p ON p.plan_id = t.plan_id "
            "WHERE t.trade_id = ? AND p.plan_id IS NULL",
            (dto.trade_id,),
        ).fetchone()["c"]
        assert n == 0, "指向不存在计划的成交不应落库（悬空引用）"

    def test_symbol_mismatch_should_be_rejected(self, conn):
        plan_id = _armed_plan(conn)  # symbol=510300
        trades.create_trade(
            conn, request_id="req-j3-202",
            plan_id=plan_id,
            **_trade_kwargs(fund_code="510500", fund_name="中证500ETF"),
        )
        conn.commit()
        n = conn.execute(
            "SELECT COUNT(*) c FROM fund_trades t JOIN trade_plans p "
            "ON p.plan_id = t.plan_id WHERE t.fund_code != p.symbol"
        ).fetchone()["c"]
        assert n == 0, "成交标的与计划标的不符时不应落库"

    def test_direction_mismatch_should_be_rejected(self, conn):
        plan_id = _armed_plan(conn)  # direction=long（对应买入方向）
        trades.create_trade(
            conn, request_id="req-j3-203",
            plan_id=plan_id,
            **_trade_kwargs(side="sell"),  # 做多计划记卖出方向
        )
        conn.commit()
        n = conn.execute(
            "SELECT COUNT(*) c FROM fund_trades t JOIN trade_plans p "
            "ON p.plan_id = t.plan_id "
            "WHERE (p.direction = 'long' AND t.side = 'sell') "
            "   OR (p.direction = 'short' AND t.side = 'buy')"
        ).fetchone()["c"]
        assert n == 0, "成交方向与计划方向不符时不应落库"
