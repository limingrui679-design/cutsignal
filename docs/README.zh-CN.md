# CutSignal 中文说明

CutSignal 把三个原本分散的问题放进一个可审计项目：减脂趋势是否真的停滞、减重期间力量是否在下降、以及在预算和营养不确定性下能否形成可执行的周食谱。

它不是 Apple Watch 专用项目。Apple Health 是首个原生适配器；核心模型接受通用 CSV/JSONL，可承接 Garmin、Fitbit、COROS、电子秤、饮食记录和训练 App 的标准化导出。

主要输出不是“继续减卡”，而是证据门禁：

- `continue`：趋势仍在目标带外，继续一致记录；
- `collect_more_data`：体重、摄入覆盖或 TDEE 区间不足；
- `review_recovery_first`：力量下降与疲劳信号同时出现，先检查恢复；
- `consider_plan_review`：平台概率、数据覆盖和敏感性稳定性均过门槛，可考虑人工复核；
- `validate_food_data`：食谱过度依赖低置信度营养或价格记录。

快速演示：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cutsignal demo --output artifacts/demo
cutsignal ui
```

演示数据完全合成。项目不决定个人应该摄入多少热量或以多快速度减重，也不能替代医生或注册营养师。
