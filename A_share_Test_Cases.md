# A_share 项目 — 测试用例文档

> **项目名称**：A_share — A 股技术分析指标系统
> **版本**：1.0
> **日期**：2026-04-10
> **覆盖范围**：Jurik Breakout 指标 + 数据获取 + 全流程集成
> **审批人**：SimonLiao

---

## 1. 测试策略总览

### 1.1 测试分层

```
┌──────────────────────────────────────┐
│         回归测试（Regression）         │ ← 用真实 CSV 快照检测重大变更
├──────────────────────────────────────┤
│         集成测试（Integration）        │ ← 端到端：CSV → 指标 → 文件
├──────────────────────────────────────┤
│         组件测试（Component）          │ ← JurikBreakoutIndicator.compute
├──────────────────────────────────────┤
│         单元测试（Unit）               │ ← JMA / ATR / Pivot / StateMachine
└──────────────────────────────────────┘
```

### 1.2 测试文件与测试类

| 测试文件 | 测试类 | 级别 |
|----------|--------|------|
| `tests/unit/test_indicator_core.py` | `TestIndicatorCore` | 单元 |
| `tests/integration/test_jurik_pipeline.py` | `TestJurikPipeline` | 集成 |
| `tests/regression/test_jurik_regression.py` | `TestJurikRegression` | 回归 |

### 1.3 测试数据源

**真实 CSV 文件**（`data/daily_price/`）：
| 文件名 | 特点 | 用途 |
|--------|------|------|
| `中国中铁_20260410.csv` | 混合趋势/震荡，含完整下行段 | 主要回归基准 |
| `中国平安_20260410.csv` | 有向上突破信号 | 次要回归基准 |
| `新和成_20260410.csv` | 跨股票一致性验证 | 交叉验证 |
| `紫金矿业_20260410.csv` | 波动较大 | 边界条件验证 |

**合成 Fixtures**：
- 用于单元测试，通过 `pd.DataFrame` 手工构造
- 优点：确定性、可控、可逐行推理

---

## 2. 单元测试用例

### 2.1 JMA 模块

#### UT-01：JMA 初始化

**输入**：`close = [10.0, 11.0, 12.0]`，`length=3`，`phase=1.0`
**预期**：`jma[0] == close[0] == 10.0`
**断言**：`assert jma.iloc[0] == 10.0`

#### UT-02：JMA 递归更新

**输入**：`close = [10.0, 11.0, 12.0, 11.0]`，固定 `length` 和 `phase`
**预期**：每个 `jma[i]` 满足递归公式
**断言**：`assert abs(jma[i] - ((1-alpha)*close[i] + alpha*jma[i-1])) < 1e-6`

#### UT-03：JMA 参数验证

**输入**：`length=0` 或 `phase=0` 或空 close
**预期**：`raise ValueError`

---

### 2.2 ATR 模块

#### UT-04：ATR 预热期

**输入**：`df` 长度 = `atr_window - 1`，3 列 OHLC
**预期**：前 `atr_window - 1` 行为 `NaN`
**断言**：`assert pd.isna(atr.iloc[0])` 和 `assert pd.isna(atr.iloc[atr_window-2])`
**断言**：`assert not pd.isna(atr.iloc[atr_window-1])`

#### UT-05：ATR True Range 计算

**输入**：
```
date: 2026-01-01, 2026-01-02, 2026-01-03
high:  11,        12,          13
low:   9,         9.5,         8
close: 10,        11,          12
```
**预期**：
- day2 TR = `max(12-9, abs(12-10), abs(9-10)) = 3`
- day3 TR = `max(13-8, abs(13-11), abs(8-11)) = 5`

---

### 2.3 Pivot 模块

#### UT-06：Pivot High 延迟确认

**输入**：`high = [1.0, 3.0, 2.0, 1.0, 1.0]`，`pivot_len=1`
**预期**：
- bar 0, 1 无信号
- bar 2 确认 bar 1 的 high = 3.0（因为 bar 1 是唯一最大值）
- `ph[2] == 3.0`，`ph_idx[2] == 1`
**断言**：`assert pd.isna(pivots.loc[1, "ph"])`，`assert pivots.loc[2, "ph"] == 3.0`

#### UT-07：Pivot 并列极值拒绝

**输入**：`high = [1.0, 3.0, 3.0, 1.0, 1.0]`，`pivot_len=1`
**预期**：并列极值不产生信号，所有 `ph` 为 `NaN`
**断言**：`assert pivots["ph"].isna().all()`

#### UT-08：Pivot Low 确认

**输入**：`low = [9.0, 7.0, 8.0, 6.5, 7.0]`，`pivot_len=1`
**预期**：bar 3 确认 bar 2 的 low = 6.5
**断言**：`assert pivots.loc[3, "pl"] == 6.5`，`assert pivots.loc[3, "pl_idx"] == 2`

---

### 2.4 StateMachine 模块

#### UT-09：上轨结构形成（双极点 ATR 校验通过）

**Setup**：
```
Row 0: trend=True,  ph=10.0,  ph_idx=0,  atr=1.0  → 初始化 H=10.0, Hi=0
Row 1: trend=True,  ph=None, atr=1.0             → 无新极点
Row 2: trend=True,  ph=10.5,  ph_idx=2,  atr=1.0  → |10.5-10.0|=0.5 < 1.0 → 上轨激活
```
**预期**：
- Row 2 的 `structure_active == True`
- Row 2 的 `structure_side == "upper"`
- Row 2 的 `res_line == 10.5`

#### UT-10：上轨突破信号

**Setup**：在 UT-09 的基础上：
```
Row 3: trend=True, close=10.6, res_line=10.5, upper_active=True
```
**预期**：
- `signal == 1`
- `breakout_up == True`
- `structure_active == False`（突破后清空）

#### UT-11：下轨结构形成

**Setup**：对称于 UT-09
**预期**：`structure_active == True`，`structure_side == "lower"`，`sup_line == pl`

#### UT-12：下轨突破信号

**Setup**：对称于 UT-10
**预期**：`signal == -1`，`breakout_down == True`

#### UT-13：趋势翻转清除结构

**Setup**：先形成上轨结构，然后：
```
Row N: trend=True,  upper_active=True, res_line=10.5
Row N+1: trend=False  ← 趋势翻转
```
**预期**：
- Row N+1 的 `structure_active == False`
- `res_line == None`

#### UT-14：ATR 不满足时拒绝结构形成

**Setup**：
```
Row 0: trend=True,  ph=10.0, ph_idx=0, atr=1.0   → H=10.0
Row 1: trend=True,  ph=15.0, ph_idx=1, atr=1.0   → |15-10|=5 > ATR(1.0) → 拒绝
```
**预期**：Row 1 的 `structure_active == False`（ATR 校验失败）

#### UT-15：突破护城河（防止旧极点重建旧结构）

**Setup**：突破后：
```
BreakUp=5（Row 5 发生向上突破）
Row 10: trend=True, ph=9.8, ph_idx=9, atr=1.0   → Hi=9 > BreakUp=5 → 允许形成新结构
Row 11: trend=True, ph=9.9, ph_idx=10, atr=1.0  → Hi=10 > BreakUp=5 → |9.9-9.8|=0.1 < 1.0 → 新上轨
```

---

### 2.5 可视化模块

#### UT-16：缺失日历日期生成

**输入**：`df["date"] = ["2026-01-02", "2026-01-05", "2026-01-07"]`
**预期**：`missing = ["2026-01-03", "2026-01-04", "2026-01-06"]`
**断言**：`assert set(missing) == {"2026-01-03", "2026-01-04", "2026-01-06"}`

---

## 3. 组件测试用例

### 3.1 CT-01：完整输出列存在性

**来源**：`中国中铁_20260410.csv` 前 120 行
**断言**：
```python
required = [
    "jma", "trend", "atr",
    "ph", "pl", "ph_idx", "pl_idx",
    "res_line", "sup_line",
    "structure_active", "structure_side",
    "signal", "breakout_up", "breakout_down",
    "pivot_confirm", "pivot_type"
]
for col in required:
    assert col in result.columns
```

### 3.2 CT-02：行数与顺序不变

**来源**：同 CT-01
**断言**：`assert len(result) == len(df)`

### 3.3 CT-03：信号值域检查

**来源**：同 CT-01
**断言**：`assert set(result["signal"].unique()).issubset({-1, 0, 1})`

### 3.4 CT-04：Pivot 因果性检查

**来源**：同 CT-01，`pivot_len=4`
**断言**：
```python
for i in result.index:
    if not pd.isna(result.loc[i, "ph_idx"]):
        assert result.loc[i, "ph_idx"] <= i - 4
    if not pd.isna(result.loc[i, "pl_idx"]):
        assert result.loc[i, "pl_idx"] <= i - 4
```

### 3.5 CT-05：原始列未修改

**来源**：同 CT-01
**断言**：输入和输出的 `date`, `open`, `high`, `low`, `close`, `volume` 完全一致

---

## 4. 集成测试用例

### 4.1 IT-01：完整流水线（中国中铁）

**数据**：`data/daily_price/中国中铁_20260410.csv`
**步骤**：
1. `load_price_data()` 读取 CSV
2. `JurikBreakoutIndicator().compute()` 计算指标
3. `write_output_csv()` 写入结果
**断言**：
- 全流程无异常
- 输出文件存在
- 输出包含 `signal` 列且有至少一条有效信号

### 4.2 IT-02：四股票交叉验证

**数据**：所有 4 个真实 CSV 文件
**断言**：
- 每个文件均能成功加载
- 每个输出的行数与输入一致
- 每个输出的 schema 包含所有必需列

### 4.3 IT-03：图表生成

**数据**：IT-01 的输出
**断言**：
- HTML 文件存在
- 文件内容包含 `<html`（大小写不敏感）
- 文件大小 > 0

### 4.4 IT-04：错误日志路径

**断言**：
- `get_error_log_path()` 返回路径的父目录名为 `log`
- 文件名以 `_error.log` 结尾
- `log/` 目录在项目根目录下

---

## 5. 回归测试用例

### 5.1 RT-01：中国中铁回归快照

**数据**：`中国中铁_20260410.csv`，默认参数
**基准快照**（每次代码变更后应保持一致）：

| 字段 | 预期值 |
|------|--------|
| 总行数 | 306 |
| `signal == 1` 计数 | 0 |
| `signal == -1` 计数 | 1 |
| `pivot_confirm == True` 计数 | 40 |
| `signal == -1` 所在行索引 | `[301]` |
| 突破价位 `breakout_level` | `5.31` |
| 突破日期 | `2026-04-03` |

### 5.2 RT-02：中国平安回归快照

**数据**：`中国平安_20260410.csv`，默认参数
**基准快照**：

| 字段 | 预期值 |
|------|--------|
| `signal == 1` 计数 | 1 |
| `signal == -1` 计数 | 0 |
| `pivot_confirm == True` 计数 | 40 |

### 5.3 RT-03：全部股票冒烟测试

**数据**：全部 4 个 CSV 文件
**断言**：
- 每个文件均无异常
- 每个输出的 schema 有效
- 每个输出的行数等于输入行数

---

## 6. 边界与负面测试用例

### 6.1 EX-01：空输入

**输入**：`DataFrame = pd.DataFrame(columns=["date","open","high","low","close","volume"])`
**预期**：`raise ValueError`

### 6.2 EX-02：缺少必需列

**输入**：缺少 `close` 列
**预期**：`raise ValueError`

### 6.3 EX-03：日期不排序

**输入**：日期列为降序
**预期**：`raise ValueError`（loader 自动排序后仍不通过）

### 6.4 EX-04：close 含空值

**输入**：close 列某行为 `NaN`
**预期**：`raise ValueError`

### 6.5 EX-05：数据太短（无 pivot）

**输入**：长度 < `2 * pivot_len + 1`
**预期**：
- `pivot_confirm` 全为 `False`
- `signal` 全为 `0`
- 无 `structure_active == True`

### 6.6 EX-06：ATR 未就绪期间无结构

**输入**：长度 < `atr_window`，有 pivot 但 ATR 仍为 NaN
**预期**：即使有双极点，也不形成结构（ATR 校验失败）

---

## 7. 黄金验收示例

**参数**：`len=3, phase=1.0, pivot_len=1, atr_window=3`

**输入数据**：

| idx | close | high | low |
|-----|------:|-----:|----:|
| 0 | 10.0 | 10.2 | 9.8 |
| 1 | 10.8 | 11.0 | 10.1 |
| 2 | 10.2 | 10.4 | 9.9 |
| 3 | 10.9 | 11.1 | 10.3 |
| 4 | 10.4 | 10.5 | 10.0 |
| 5 | 11.3 | 11.5 | 10.8 |

**预期事件语义**：

| idx | 预期趋势 | 预期 pivot | 预期结构 | 预期信号 |
|----:|:--------:|:----------:|:--------:|:--------:|
| 0 | warm-up | — | — | 0 |
| 1 | warm-up | — | — | 0 |
| 2 | derived | pivot-high: idx1 确认 | 无结构（首个极点） | 0 |
| 3 | derived | — | — | 0 |
| 4 | derived | pivot-high: idx3 确认 | 若 ATR 通过，上轨激活 | 0 |
| 5 | derived | — | 上轨活跃 | `1`（若 close>res_line） |

---

## 8. 运行方式

```bash
# 运行所有测试
python -m pytest tests/ -v

# 只运行单元测试
python -m pytest tests/unit/ -v

# 只运行回归测试
python -m pytest tests/regression/ -v

# 运行指定测试类
python -m pytest tests/unit/test_indicator_core.py::TestIndicatorCore -v
```

---

## 9. 测试覆盖率目标

| 模块 | 覆盖率目标 |
|------|-----------|
| `analytics/jma.py` | ≥ 95% |
| `analytics/atr.py` | ≥ 95% |
| `analytics/pivots.py` | ≥ 90% |
| `state_machine/breakout.py` | ≥ 95% |
| `indicators/jurik_breakout.py` | ≥ 85% |
| `io/loader.py` | ≥ 90% |
| `visualization/plot_*.py` | 冒烟测试（HTML 生成即可） |
