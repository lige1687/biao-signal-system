# LEI 个人管理数据同步（多机共享自选/计划/情绪）

把本机的「管理类数据」—— **自选与分组、交易计划、情绪库镜像、情绪 CSV** ——
导出成明文 JSON + CSV，放进一个独立的 git 分支（`data-sync`），推到你的私有仓库。
另一台机器 `git clone` 该分支后，一条命令即可把数据导入本机数据库并查看。

> 这是「镜像」同步：远端覆盖本机对应表（整表替换），不是合并。
> 谁最后推送，谁就是权威。适合「个人多机、单人在用」的场景。

---

## 同步范围

| 内容 | 来源 |
|------|------|
| 自选分组 | `watchlist_groups` |
| 自选标的 | `watchlist_items` |
| 交易计划 | `trade_plans` / `trade_plan_revisions` / `plan_action_items` / `plan_annotations` |
| 情绪库镜像 | `sentiment_observations` |
| 情绪 CSV（UI 读取源） | `data/sentiment/*.csv` 或 `$LEI_SENTIMENT_ROOT/*.csv` |

**刻意不同步**：`.env` 密钥、`*.db` 本体、cache 目录、市场宽度/评估等派生快照、`feishu_webhook_nonces` 一次性令牌。
SQLite 二进制不做文件级同步（并发写会损坏），统一走「导出 JSON → git → 导入」。

---

## 机器 A（源 / 日常推送）

脚本已就位在 `scripts/sync/`。首次需要建好同步仓库与分支（见下方「初始化一次」）。
之后每天推送：

```bash
cd ~/Desktop/lei-signal-lab/scripts/sync
./sync_push.sh
```

`push.sh` 会：导出 → 切到 `data-sync` 分支 → 提交数据+脚本 → `git push -u` 到远端。

---

## 机器 B（目标 / 拉取查看）

```bash
# 1. 克隆同步分支（含代码+脚本+数据）
git clone --branch data-sync git@github.com:lige1687/biao-signal-system.git ~/lei-signal-sync

# 2. 若首次使用，先让后端初始化 db schema（建表），再停掉后端
biao start        # 跑一次，自动建表
biao stop

# 3. 拉取并导入（会整表替换本机对应表，并自动备份旧 db）
cd ~/lei-signal-sync/scripts/sync
./sync_pull.sh

# 4. 启动查看
biao start
```

之后每次同步只需 `./sync_pull.sh`（内部已 `git fetch` + 导入）。

---

## 初始化一次（仅机器 A 首次）

在机器 A 上把 `~/lei-signal-sync` 建成 `data-sync` 分支的工作树：

```bash
cd ~/Desktop/lei-signal-lab
git worktree add ~/lei-signal-sync data-sync
# 把同步脚本也带进该分支（主分支 recovery/lei-round2 保持不动）
mkdir -p ~/lei-signal-sync/scripts/sync
cp ~/Desktop/lei-signal-lab/scripts/sync/* ~/lei-signal-sync/scripts/sync/
```

然后正常 `./sync_push.sh` 即可（首次会创建远端 `data-sync` 分支）。

---

## 环境变量（可选覆盖，适配不同机器/远端）

| 变量 | 默认 | 说明 |
|------|------|------|
| `LEI_SYNC_DIR` | `$HOME/lei-signal-sync` | 同步包仓库路径 |
| `LEI_SYNC_REMOTE` | `git@github.com:lige1687/biao-signal-system.git` | 远端地址 |
| `LEI_SYNC_BRANCH` | `data-sync` | 分支名 |
| `LEI_SQLITE_PATH` | `$HOME/.lei_signal_lab/lab.db` | 本机 SQLite |
| `LEI_PROJECT_DIR` | 脚本上两级 | 项目根（定位情绪 CSV） |
| `LEI_SENTIMENT_ROOT` | `<项目>/data/sentiment` | 情绪 CSV 目录 |
| `LEI_SYNC_PORT` | `8000` | 后端端口（导入预检占用） |
| `LEI_SYNC_PYTHON` | `python3` | Python 解释器 |

---

## 安全与回滚

- **密钥永不同步**：`.env` 不在范围内，推送前请确认同步包里没有 `.env` / `*.db`。
- **导入自动备份**：导入前会把本机 db 复制为 `<db>.bak-<时间戳>`，出错可回滚。
- **后端占用保护**：后端运行时导入会被拒绝（exit 2），避免写冲突。
- **镜像覆盖**：导入是整表 DELETE+INSERT，本机「未推送的本地改动」会被远端覆盖。
  若需保留本地，先 `./sync_push.sh` 再在另一台 `./sync_pull.sh`。
