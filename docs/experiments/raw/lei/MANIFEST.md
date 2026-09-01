# LEI组归档清单（2026-09-01）

19 轮实验原始数据副本（源目录不迁移，本目录为归档快照）：
- module_e_results.json：模块E手册口径（美股40年/A股，v1/v3/事件研究/对冲分段）
- breadth_overlay_results.json：宽度叠加四轮（两档制/强平/混合/分账/背离/停新买）
- symbol_tilt_results.json：标的优选软倾斜（判负） 
- final_form_v2_results.json：完整形态v2（判负，F0卫冕）
- dual_speed_gate_results.json：双速闸（判负）
- caliber_check_results.json：CSI300口径检验+前段核验
- walkforward_results.json + wf_equity{,_fixed}.csv：终审七折
- per_symbol_attr.csv / symbol_report_card.csv：96标的逐个成绩
- index_showcase.csv：指数三形态对比
- a_share_breadth_33y_snapshot.json：全A宽度33年快照
- sentiment_*.json / position_gate / fundamental_panel / rate_gate：信息源四轮
- 数据：乐咕仓位/NAAIM/中美国债/PMI/两融信号

复现：PYTHONHASHSEED=0 python3 scripts/run_*.py（各脚本 docstring 含事前判定标准）
报告：web/public/reports/lei-zuhe-zhongshen-2026-09-01.html
