# 运行台账（编号留痕，绝不删除复用）
## 2026-09-15 22:31:25 make_package.py run-01（正式拼装第1次）
run-01: rows=1558 complete=False duplicates_deduped=72 extra_quarantined=1764
exit=2
## 2026-09-15 22:31:25 restore_check.py run-01（恢复演练，临时目录只读）
FAIL: prices.csv 逐日覆盖与日历推导不一致
恢复演练：失败
OK: 包内 14 项文件哈希与集合双向一致
OK: 七份原件+fetch-manifest+日历+协议+assemble.py 原字节一致
OK: 全部价格正有限、日期唯一递增
OK: quality 声明齐全（real/历史重构/available_at=null/anchor unknown）
exit=1
## 2026-09-15 23:05:15 纠错：assemble窗口语义+restore tuple==list；单测重跑
.........                                                                [100%]
9 passed in 0.14s
## 2026-09-15 23:05:15 make_package.py run-02（修正后新编号，第2次即末次）
run-02: rows=1558 complete=True duplicates_deduped=72 extra_quarantined=0
exit=0
## 2026-09-15 23:05:15 restore_check.py run-02（恢复演练）
OK: 包内 14 项文件哈希与集合双向一致
OK: 七份原件+fetch-manifest+日历+协议+assemble.py 原字节一致
OK: prices.csv 逐日覆盖==日历推导（1558 个交易日）
OK: 全部价格正有限、日期唯一递增
OK: quality 声明齐全（real/历史重构/available_at=null/anchor unknown）
恢复演练：通过 —— 仅只读身份/依赖核验，未调用真实研究入口
exit=0
## 2026-09-15 23:08:46 ruff（本任务文件）
E501 Line too long (107 > 100)
  --> docs/experiments/raw/510300-offline-reuse-2026-09-15/make_package.py:29:101
   |
27 | FETCH_DIR = ROOT / "docs/experiments/raw/research-third-2026-09-08/06"
28 | FETCH_MANIFEST = FETCH_DIR / "fetch-manifest.json"
29 | VERIFICATION = ROOT / "docs/experiments/raw/factor-unit-four-fixes-controller-2026-09-15/verification.json"
   |                                                                                                     ^^^^^^^
30 | CALENDAR = ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json"
31 | COVER_START, COVER_END = "2019-09-02", "2026-02-03"
   |

E501 Line too long (110 > 100)
  --> docs/experiments/raw/510300-offline-reuse-2026-09-15/make_package.py:30:101
   |
28 | FETCH_MANIFEST = FETCH_DIR / "fetch-manifest.json"
29 | VERIFICATION = ROOT / "docs/experiments/raw/factor-unit-four-fixes-controller-2026-09-15/verification.json"
30 | CALENDAR = ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json"
   |                                                                                                     ^^^^^^^^^^
31 | COVER_START, COVER_END = "2019-09-02", "2026-02-03"
32 | CROSS_CHECK_ROWS = 1558  # 主控交叉证据；放行闸门是逐日推导，不是行数
   |

E501 Line too long (110 > 100)
  --> docs/experiments/raw/510300-offline-reuse-2026-09-15/restore_check.py:28:101
   |
27 | FETCH_DIR = ROOT / "docs/experiments/raw/research-third-2026-09-08/06"
28 | CALENDAR = ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json"
   |                                                                                                     ^^^^^^^^^^
29 | COVER_START, COVER_END = "2019-09-02", "2026-02-03"
   |

Found 3 errors.
exit=1
## 2026-09-15 23:08:46 相关回归第1次（上限1次）：七文件pytest
.....................................                                    [100%]
108 passed, 1 skipped in 5.56s
exit=0
## 2026-09-15 23:09:32 ruff 复检（纠错：E501×3）
All checks passed!
exit=0
