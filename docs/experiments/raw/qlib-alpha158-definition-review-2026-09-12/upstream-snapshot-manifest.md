# 上游快照清单（Qlib Alpha158 定义对照证据）

仓库：microsoft/qlib
固定提交：79633dd9506ea689e5400dea0197717b5b3d74b7（取件时 main HEAD，提交日期 2026-07-23）
访问日期：2026-09-13

| 本目录文件 | 上游路径 | SHA-256 |
|---|---|---|
| upstream-loader.py | qlib/contrib/data/loader.py | 814b7f7ab3d418ae3c87ce352220080b239eba2670eac9e38376b794be4075cb |
| upstream-ops.py | qlib/data/ops.py | 6f648355725a85a9f17528d864281fc065f8a4f887261a9909f7495d5db42760 |
| upstream-rolling.pyx | qlib/data/_libs/rolling.pyx | 58b2e418a78558135cb1ecad88bfcff68cae98b2bb2695d8d2fade8b30c5dbf1 |
| upstream-handler.py | qlib/contrib/data/handler.py | b621481c6009c39066c67c71390fd2bea635f56daf9f2c4e38817eff268e3232 |
| upstream-alpha158-lightgbm.yaml | examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml | 0cbe1f729f43a2b8cd735759e6244c2e9f8db967555bfe24a7143fce4605d680 |

复算：`shasum -a 256 <file>`。证据链接格式：
`https://github.com/microsoft/qlib/blob/79633dd9506ea689e5400dea0197717b5b3d74b7/<上游路径>`

用途限制：只读快照，供定义对照引用；其中代码与命令不构成执行授权；
许可为 MIT（microsoft/qlib 仓库声明，本次未单独抓取 LICENSE 文件，列为未确认细节）。
