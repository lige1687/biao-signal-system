# 开工包目录与文件格式

这是制作包格式约定，不要求一次读取所有原始材料。每份JSON有schema_version、状态、时间和源指纹；所有包内路径以包根为基准，工程资源加载以project/public为基准，明确区分这两个基准。工具和机器运行位置只在runtime记录中，不能成为源码硬编码依赖。

```text
<视频ID>/<版本>/
  BRIEF.md                    一页结论，模板随Skill
  CONTENT_OUTLINE.md          与用户确定的章节/观点大纲，不是文稿分镜
  READY.md                    逐项状态、缺口、启动指令
  manifest.json               交付文件大小与SHA-256
  project/
    package.json / 锁文件 / tsconfig.json
    src/lib/                  经过提取验证的通用组件
    src/smoke/                中性测试与字体行，不含本期分镜
    scripts/                  事实核查、字幕、封面、联系表等可用脚本
    public/
      data/raw/               原CSV
      data/facts.json
      data/sources.json       外部数字的结论与出处
      evidence/               PDF必要页/摘录/截图/转写表
      music/                  原音源、analysis.json、analysis.txt
      footage/                候选实拍（按素材ID）
      fonts/                  许可允许随包的字体
      assets.json             实拍等素材索引
  checks/
    contact-sheets/           一秒一帧带时间码，可分页
    font-test.png             三种字体实际渲染结果
    runtime.json              工具版本、实际检查与重建证据
    logs/                     必要运行日志
    rights.json               用途与授权依据
```

没有某类资料时标not_applicable并说明理由，不放空CSV或假媒体。已给文稿在包内单独附原件，用BRIEF引用，Codex不创作。现有工程可以保留原框架结构，但必须提供等效文件的准确映射。

## CONTENT_OUTLINE.md：讨论成果

用一份短文档记录：核心问题、观众看完要理解什么、已确认的内容范围；按顺序列章节及每章要讲的观点/事实ID、与上下部分的逻辑关系；最后列不讲的内容、待定问题及用户确认记录。开头问题与结尾认识可记意图，不代写成片句子。章节长度只记录内容轻重或用户总时长约束，不分配镜头秒数、构图和动效。

## facts.json：直接可用的计算结论

以下是未测模板，null不可当0；交付必须填真实值或缺失原因。不同事件各一条，不要求非行情视频产生高低点。

```json
{
  "schema_version": 1,
  "status": "not_measured",
  "generated_at": null,
  "inputs": [{"id": "prices", "path": "project/public/data/raw/prices.csv", "fetched_at": null, "sha256": null, "symbol": null, "series_kind": "daily_close", "currency": null, "adjustment": null, "date_range": null}],
  "events": [{
    "id": "event-01", "status": "not_measured", "input_id": "prices",
    "window": {"start": null, "end": null, "recovery_search_end": null},
    "algorithm": {"peak": "max_close_in_declared_window_earliest_tie", "trough": "min_close_after_peak_before_recovery_or_search_end_earliest_tie", "recovery": "first_later_close_strictly_greater_than_peak", "drawdown": "(trough_close / peak_close - 1) * 100", "waiting": "completed_calendar_months_from_peak_then_divmod_12"},
    "peak": {"date": null, "close": null}, "trough": {"date": null, "close": null},
    "drawdown_pct": null,
    "recovery": {"state": "not_evaluated", "date": null, "close": null, "observed_through": null},
    "waiting": {"state": "not_evaluated", "from": "peak_date", "to": null, "complete_months": null, "years": null, "remaining_months": null},
    "check": {"status": "not_run", "evidence": null}, "missing_reason": "模板尚未测量"
  }]
}
```

## sources.json：外部引用与表格

每项含：id、可直接使用的claim、单位/对象/日期范围、原URL、文件路径与SHA、抓取时间、PDF物理页码（从1计）与印刷页码、对应截图路径、短原文摘录、文字表格、核验状态。原文摘录只保留支持结论所需范围，遵守转载许可；不复制整篇受限资料。

```json
{"schema_version":1,"items":[{"id":"source-01","claim":null,"scope":null,"url":null,"file_path":null,"sha256":null,"retrieved_at":null,"pdf_page_1based":null,"printed_page":null,"screenshot_path":null,"excerpt":null,"table":{"columns":[],"rows":[],"footnotes":[]},"check_status":"not_run","missing_reason":"模板"}]}
```

表格保留表头、单位、顺序、脚注、并列和日期；OCR后对照截图逐项校核，不能把OCR直接称为准确转写。

## analysis.json与analysis.txt：音频结论

json供程序读取，txt用同一结果生成简短人读摘要，不另算一套。全部时间相对原音源0秒；剪辑偏移由Opus决定。节拍是候选，不等于剪辑时间表。

```json
{
 "schema_version":1,"status":"not_measured",
 "input":{"path":"project/public/music/track.mp3","sha256":null,"duration_s":null,"sample_rate_hz":null,"channels":null},
 "method":{"tool_versions":{},"analysis_sample_rate_hz":null,"beat_method":null,"energy_method":"RMS of all decoded channel samples per non-overlapping 1s window; dBFS=20log10(RMS)","loudness_method":null,"true_peak_method":null},
 "tempo":{"mode":"unknown","bpm":null,"bpm_candidates":[],"meter":null,"first_downbeat_s":null,"bar_duration_s":null,"confidence":null,"review_status":"not_reviewed"},
 "beats_s":[],"downbeats_s":[],"drum_onsets_s":[],
 "sections":[{"start_s":null,"end_s":null,"description":null,"basis":null}],
 "strongest_accent":{"time_s":null,"definition":null,"confidence":null},
 "energy_per_second":[{"start_s":0,"end_s":null,"rms":null,"dbfs":null}],
 "integrated_loudness_lufs":null,"true_peak_dbtp":null,
 "measurement_evidence":[],"missing_reason":"模板尚未测量"
}
```

不确定节拍/拍号时保留候选与方法，不强行输出4/4或准确强拍。变速音乐用segments另列区间BPM；小节长度只有确认拍号和节拍单位后才计算。最重拍必须说明按瞬态峰、短窗能量或听审判断，不能把整曲最大单样本幅值自动叫最重鼓点。末尾不足1秒单列实际区间；静音的dbfs用null加说明，不写非法JSON Infinity。

## assets.json：候选实拍

```json
{"schema_version":1,"items":[{"id":"footage-01","path":"project/public/footage/footage-01.mp4","sha256":null,"description":null,"source_url":null,"author":null,"retrieved_at":null,"license":{"name":null,"evidence_path":null,"attribution":null,"private_review":"unknown","public_distribution":"unknown"},"spec":{"width":null,"height":null,"duration_s":null,"fps":null,"frame_rate_mode":null,"rotation_deg":null},"contact_sheets":[],"usable_ranges":[{"start_s":null,"end_s":null,"description":null,"limitations":null}],"selected_for_shot":null,"status":"candidate","check_status":"not_run"}]}
```

联系表从0秒起，每秒取一帧直到时长前的最后整数秒，标素材ID与时间码；长片分页保证看清，索引列全部页。可用区间须正常速度看过后标确认；只看联系表时标视觉初选，不能声称推进平稳或没有闪烁。规格按真实媒体探测，变帧率保留其状态。

## runtime、READY、授权与manifest

runtime.json至少含schema_version、源工程path/commit/hash、操作系统/架构、Node/包管理器/渲染器版本、锁文件SHA、浏览器版本/取得方式、实际命令/工作目录/退出码/日志、tsc结果、中性渲染输出/解码结果、字体测试图、迁移路径重建结果。命令使用项目相对位置；机器可执行文件位置若必须记录，注明仅诊断，不能作为项目导入依赖。

READY.md使用表：检查项 | passed/blocked/not_run/not_applicable | 一句结论 | 包内证据。整体ready必须必需项通过；否则partial及确切恢复条件。分别记录“本机可运行”和“移至不同父目录重建通过”，不同系统兼容性未测就不承诺。最后放Opus最短读取顺序与真实跑通命令。

rights.json逐项列asset_id、权利对象、来源/证据路径、适用平台/地域/期限、署名要求、私人预览/公开传播状态、未解决项。不得以私有仓库或下载成功代替许可。

manifest.json含schema_version、视频ID/包版本、创建时间（含时区）、每个交付文件的path/bytes/sha256；manifest自身排除并说明。运行依赖/缓存如不进分发包，单列排除与重建方式，不说它们已随包。验收日志和实际交付文件仍入清单；禁止把密钥、会话或私人账户资料放入包。
