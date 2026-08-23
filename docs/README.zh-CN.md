# CutSignal 中文说明

CutSignal 把三个原本分散的问题放进一个可审计项目：减脂趋势是否真的停滞、减重期间力量是否在下降、以及在预算和营养不确定性下能否形成满足约束的周食谱。

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
python -m pip install -e '.[ui]'
cutsignal doctor
cutsignal demo --output artifacts/demo
cutsignal ui
```

演示数据完全合成。它同时生成两类报告：`private` 会包含日期、逐日体重/摄入、潜在
TDEE、训练和菜单细节；`share-safe` 会从结构上删除日期、逐日序列、精确健康指标、
动作和食品名称及菜单，但保留的派生类别仍可能敏感，也不能保证匿名。

项目内置 9 个可执行合成案例，用来展示缺失摄入时主动拒绝判断、单次水重冲击、力量
下降与 RPE/训练量共同触发恢复优先、预算冲击、素食与过敏原约束、手机/手表重叠步数
对账，以及通用外部形态 CSV 的别名、单位、重复日和来源迁移等不同能力：

```bash
cutsignal cases list
cutsignal cases verify --output artifacts/cases.json
```

近期体重变化率直接来自保持谱系关系的粒子轨迹，不再用两个边际区间的独立正态近似。
力量趋势采用 e1RM 公式不确定性加权回归和明确标注的经验贝叶斯收缩；饮食规划会在
求解器之外重新核验全部硬约束。五个目标权重产生的是“抽样后的非支配折中集合”，
不是完整 Pareto 前沿。

`python scripts/evaluate_synthetic.py` 会在 12 个预先固定的已知真值合成情景中，把粒子
轨迹近期变化率与同窗口 OLS 基线比较，并保留逐情景误差、区间覆盖、Brier 分数和误判。
这是内部合成压力测试，不是外部校准、群体表现或临床有效性。

项目不决定个人应该摄入多少热量或以多快速度减重，也不能替代医生或注册营养师。
当前没有声称真实用户、外部评审、临床验证、采用或现实影响。

方法来源、实际借用内容和不能迁移证明的边界见[方法参考与迁移边界](REFERENCES.md)。引用
文献只说明算法家族或上游字段来源，不构成 CutSignal 的外部校准或临床验证。
