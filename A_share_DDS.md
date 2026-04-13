# A_share 项目 — 详细设计文档（DDS）

> **项目名称**：A_share — A 股技术分析指标系统
> **版本**：1.0
> **日期**：2026-04-10
> **参考基准**：`doc/Jurik`（TradingView Pine Script v6 源码）
> **审批人**：SimonLiao

---

## 1. 目的

本文档定义 A_share 项目各模块的详细设计规范，包括：数据合约、算法公式、状态机规则、输出模式、错误处理和运行时路径。

---

## 2. 数据合约

### 2.1 输入 CSV 格式

```csv
date,open,high,low,close,volume
2025-01-02,21.07,21.56,20.60,20.68,650000.0
2025-01-03,20.68,21.20,20.55,20.76,720000.0
...
```

| 列名 | 类型 | 约束 |
|------|------|------|
| `date` | YYYY-MM-DD 字符串 | 升序排列，唯一，无重复 |
| `open` | float | >= 0 |
| `high` | float | >= max(open, close, low) |
| `low` | float | <= min(open, close, high) |
| `close` | float | >= 0，非空 |
| `volume` | float | >= 0 |

### 2.2 输入前置条件

| 检查项 | 失败处理 |
|--------|----------|
| 缺少必需列（date/open/high/low/close/volume） | `raise ValueError("missing required columns")` |
| 空 DataFrame | `raise ValueError("input data is empty")` |
| `close` 含空值 | `raise ValueError("close column contains null values")` |
| 日期非升序 | 自动排序后二次验证，若仍失败则 `raise ValueError` |
| 日期有重复 | `raise ValueError("date column contains duplicates")` |

### 2.3 输出 CSV 列清单

**原始列（保留）**：
`date`, `open`, `high`, `low`, `close`, `volume`

**指标列（新增）**：

| 列名 | 类型 | 说明 |
|------|------|------|
| `jma` | float | Jurik 移动平均线值 |
| `trend` | bool | True=上涨趋势，False=下跌趋势 |
| `atr` | float | 平均真实波幅（前 `atr_window-1` 行为 NaN） |
| `ph` | float/NaN | 确认的局部高点价格（仅在确认 K 线上有值） |
| `pl` | float/NaN | 确认的局部低点价格（仅在确认 K 线上有值） |
| `ph_idx` | int/NaN | 局部高点所属行的源索引 |
| `pl_idx` | int/NaN | 局部低点所属行的源索引 |
| `pivot_confirm` | bool | 本行是否确认了极点 |
| `pivot_type` | str/None | `"high"`、`"low"` 或 `None` |
| `res_line` | float/NaN | 当前活跃的上轨阻力线价格 |
| `sup_line` | float/NaN | 当前活跃的下轨支撑线价格 |
| `res_line_start_idx` | int/NaN | 上轨起点索引 |
| `res_line_end_idx` | int/NaN | 上轨终点索引 |
| `sup_line_start_idx` | int/NaN | 下轨起点索引 |
| `sup_line_end_idx` | int/NaN | 下轨终点索引 |
| `structure_active` | bool | 当前是否有活跃结构 |
| `structure_side` | str/None | `"upper"`、`"lower"` 或 `None` |
| `structure_event` | bool | 本行是否**新建**了结构（结构形成事件） |
| `structure_event_side` | str/None | 新建结构的类型 |
| `structure_event_pivot1_idx` | int/NaN | 结构第一个极点索引 |
| `structure_event_pivot1_price` | float/NaN | 结构第一个极点价格 |
| `structure_event_pivot2_idx` | int/NaN | 结构第二个极点索引 |
| `structure_event_pivot2_price` | float/NaN | 结构第二个极点价格 |
| `signal` | int | `1`（买入）、`0`（观望）、`-1`（卖出） |
| `breakout_up` | bool | 本行是否触发向上突破 |
| `breakout_down` | bool | 本行是否触发向下突破 |
| `breakout_level` | float/NaN | 突破发生时的结构线价格 |
| `jma_glow` | float | JMA 曲线（用于图表发光效果） |

---

## 3. 核心算法详述

### 3.1 JMA（Jurik 移动平均）

**参考**：`src/analytics/jma.py`

```python
def compute_jma(close: pd.Series, length: int, phase: float) -> pd.Series:
    beta  = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
    alpha = beta ** phase
    # 逐行递归
    jma[0] = close[0]
    for i in range(1, len(close)):
        jma[i] = (1 - alpha) * close[i] + alpha * jma[i-1]
    return jma
```

- 必须**逐行迭代**，不得向量化
- `length <= 0` 或 `phase <= 0` → `raise ValueError`
- `jma[0]` 初始化为 `close[0]`

### 3.2 Trend（趋势判断）

**参考**：`src/analytics/jma.py`

```python
def derive_trend(jma: pd.Series, lag: int = 3) -> pd.Series:
    trend = pd.Series(False, index=jma.index)
    trend.iloc[lag:] = (jma.iloc[lag:] >= jma.shift(lag).iloc[lag:]).astype(bool)
    return trend
```

- 前 `lag` 行 trend 固定为 `False`（lag 默认值 = 3）
- `lag <= 0` → `raise ValueError`

### 3.3 ATR（平均真实波幅）

**参考**：`src/analytics/atr.py`

```python
def compute_atr(df: pd.DataFrame, window: int = 200) -> pd.Series:
    # 使用 pandas-ta，smoothing mode = RMA（等同于 Pine 的 ta.atr）
    atr = ta.atr(
        high=df["high"].astype(float),
        low=df["low"].astype(float),
        close=df["close"].astype(float),
        length=window,
        mamode="rma",    # 指数移动平均（Pine 等价）
        talib=False
    )
    return atr
```

- `window <= 0` → `raise ValueError`
- 前 `window - 1` 行 ATR 为 NaN（预热期）
- 预热期内**不形成结构**，不发出信号

### 3.4 Pivot（极点检测）

**参考**：`src/analytics/pivots.py`

极点语义：Pivot 属于 `pivot_idx = i - pivot_len`，但**仅在确认 K 线 `i` 上才可见**。

```
窗口 = [i - 2*pivot_len, ..., i]
       pivot_idx = i - pivot_len（中心位置）
       
pivot high 确认条件：
  1. high[pivot_idx] 是窗口内的唯一最大值（不允许并列）
  2. 确认发生在 bar i

pivot low 确认条件：
  1. low[pivot_idx] 是窗口内的唯一最小值（不允许并列）
  2. 确认发生在 bar i
```

```python
for i in range(2 * pivot_len, len(df)):
    pivot_idx = i - pivot_len
    start     = i - 2 * pivot_len
    stop      = i + 1

    high_window = high.iloc[start:stop]
    low_window   = low.iloc[start:stop]

    # 必须唯一极值，不允许并列
    if high.iloc[pivot_idx] == high_window.max() and (high_window == high.iloc[pivot_idx]).sum() == 1:
        ph[i]     = high.iloc[pivot_idx]
        ph_idx[i] = pivot_idx

    if low.iloc[pivot_idx] == low_window.min() and (low_window == low.iloc[pivot_idx]).sum() == 1:
        pl[i]     = low.iloc[pivot_idx]
        pl_idx[i] = pivot_idx
```

- `pivot_len < 1` → `raise ValueError`
- 极点并列时**不产生信号**（防止误判）

### 3.5 Breakout State Machine（突破状态机）

**参考**：`src/state_machine/breakout.py`

#### 状态变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `H`, `Hi` | float, int | 当前已确认的最近局部高点价格和索引 |
| `L`, `Li` | float, int | 当前已确认的最近局部低点价格和索引 |
| `BreakUp`, `BreakDn` | int | 上次向上/向下突破发生的 bar 索引 |
| `upper_active` | bool | 上轨结构是否活跃 |
| `lower_active` | bool | 下轨结构是否活跃 |
| `res_line_value` | float | 上轨阻力线价格 |
| `sup_line_value` | float | 下轨支撑线价格 |
| `prev_trend` | bool | 上一行的趋势状态 |

#### 上轨结构逻辑（上涨趋势）

**结构形成条件**（同时满足）：
1. `trend == True`（当前为上涨趋势）
2. `upper_active == False`（当前无上轨结构）
3. 本行确认了新的 `ph`
4. `H is not None`（之前已有极点）
5. `Hi > BreakUp`（新极点索引在最近突破点之后）
6. `abs(ph - H) < atr`（两个极点价差小于 ATR）

**结构形成动作**：
- `upper_active = True`
- `res_line_value = ph`（新极点成为阻力线）
- `res_line_start_idx = ph_idx`
- `res_line_end_idx = i`（当前行）

**极点追踪**（上涨趋势中）：
- 每次确认 `ph` 时，更新 `H = ph`，`Hi = ph_idx`

**上轨突破条件**：
- `upper_active == True` 且 `close > res_line_value`

**突破动作**：
- `signal = 1`
- `breakout_up = True`
- `BreakUp = i`
- 调用 `_clear_upper()` 清空上轨状态

#### 下轨结构逻辑（下跌趋势）

**结构形成条件**（同时满足）：
1. `trend == False`（当前为下跌趋势）
2. `lower_active == False`（当前无下轨结构）
3. 本行确认了新的 `pl`
4. `L is not None`
5. `Li > BreakDn`
6. `abs(pl - L) < atr`

**结构形成动作**：
- `lower_active = True`
- `sup_line_value = pl`
- `sup_line_start_idx = pl_idx`
- `sup_line_end_idx = i`

**极点追踪**（下跌趋势中）：
- 每次确认 `pl` 时，更新 `L = pl`，`Li = pl_idx`

**下轨突破条件**：
- `lower_active == True` 且 `close < sup_line_value`

**突破动作**：
- `signal = -1`
- `breakout_down = True`
- `BreakDn = i`
- 调用 `_clear_lower()` 清空下轨状态

#### 趋势翻转重置

```python
if prev_trend is not None and trend != prev_trend:
    _clear_upper()   # 清空上轨
    _clear_lower()   # 清空下轨
```

- **保留** `H`、`Hi`、`L`、`Li`、`BreakUp`、`BreakDn`
- 只清空活跃结构，不重置极点记录

#### 调用规则

- 必须按**升序索引**逐行调用 `update(idx, row)`
- 不得跳过行，不得乱序
- `prev_trend` 跟踪上一行趋势，用于检测翻转

---

## 4. 数据流（端到端）

```
输入 CSV
  │
  ▼
load_price_data()              [loader.py]
  │ - 读 CSV → 解析日期 → 排序 → 验证 schema
  ▼
JurikBreakoutIndicator.compute()[jurik_breakout.py]
  │
  ├─ compute_jma(close, len, phase)           [jma.py]
  │     → jma 列
  │
  ├─ derive_trend(jma, lag=3)                 [jma.py]
  │     → trend 列
  │
  ├─ compute_atr(df, atr_window)              [atr.py]
  │     → atr 列
  │
  ├─ detect_pivots(df, pivot_len)            [pivots.py]
  │     → ph, pl, ph_idx, pl_idx 列
  │
  └─ BreakoutStateMachine.update() 逐行调用    [breakout.py]
        → res_line, sup_line, structure_active,
          structure_side, signal, breakout_up, breakout_down
        → plus: structure_event*, breakout_level
  │
  ▼
assemble_output() → 最终 DataFrame
  │
  ├─ write_output_csv(result, path)           [writer.py]
  │     → output/result_csv/<name>_jurik_breakout_result.csv
  │
  └─ plot_jurik_breakout(result, path)       [plot_*.py]
        → output/charts/<name>_jurik_breakout.html
```

---

## 5. 模块详细设计

### 5.1 `src/io/loader.py`

```python
REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

def validate_ohlcv_schema(df, require_sorted=True) -> None
    # 检查必需列、非空、日期升序、无重复

def load_price_data(path: str | Path) -> pd.DataFrame
    # 读 CSV → 解析日期 → 转数值 → 排序 → 验证
```

### 5.2 `src/io/writer.py`

```python
def get_project_root() -> Path
    # 返回项目根目录（resolve parents[2]）

def ensure_directory(path) -> Path
    # mkdir -p

def generate_output_filename(symbol: str, indicator: str) -> str
    # <symbol>_<indicator>_result.csv

def get_error_log_path(indicator_name: str, log_dir: str = "log") -> Path
    # log/<indicator_name>_<YYYYMMDD>_error.log
    # 自动创建 log 目录

def write_output_csv(df, output_path) -> Path
    # 写入 CSV（utf-8），自动创建父目录
```

### 5.3 `src/indicators/engine.py`

```python
class IndicatorEngine:
    _registry: dict[str, type[BaseIndicator]]

    def register(name: str, indicator_cls) -> None
        # 重复注册 → raise ValueError

    def run(name: str, df, config=None) -> pd.DataFrame
        # 未注册名称 → raise KeyError
        # 实例化 → config merge → compute()
```

### 5.4 `src/indicators/jurik_breakout.py`

```python
class JurikBreakoutIndicator(BaseIndicator):
    DEFAULT_CONFIG = {
        "len": 9,
        "phase": 0.15,
        "pivot_len": 4,
        "atr_window": 200,
    }

    def validate_config() -> None:
        # len > 0, phase > 0, pivot_len >= 1, atr_window >= 1

    def compute(df) -> pd.DataFrame:
        # 复制输入 → 日期解析 → 排序 → 验证 schema
        # → JMA → Trend → ATR → Pivot → StateMachine（逐行）
        # → 拼接所有列 → 填充 signal 和 breakout_level
        # → 返回结果（不修改原始 df）
```

### 5.5 `src/visualization/plot_jurik_breakout.py`

渲染层次（从底到顶）：

| 顺序 | 层 | 说明 |
|------|-----|------|
| 1 | 蜡烛图 | K 线（阳线绿色，阴线红色） |
| 2 | JMA 曲线 | 按趋势分段着色（绿/蓝），含发光层 |
| 3 | 阻力线 | 上轨虚线段（仅结构活跃期间） |
| 4 | 支撑线 | 下轨虚线段（仅结构活跃期间） |
| 5 | 结构极点连线 | 两个极点之间的虚线连接 + ✓ 标记 |
| 6 | 向上突破标记 | ↑ Break Up 箭头（绿色） |
| 7 | 向下突破标记 | ↓ Break Dn 箭头（蓝色） |

**关键函数**：
- `_iter_trend_segments(df)`：按趋势变化分段，用于 JMA 分色渲染
- `_iter_level_segments(...)`：提取活跃结构段的起止索引和价位
- `_plot_structure_events(...)`：渲染极点对之间的虚线连接
- `_build_missing_calendar_dates(df)`：生成日历缺口（用于隐藏非交易日）

---

## 6. 数据获取模块（DDS）

### 6.1 AKShare 接口映射

| 资产类型 | 主接口 | 备用接口 | 复权方式 |
|----------|--------|----------|----------|
| A 股股票 | `stock_zh_a_hist`（东方财富） | `stock_zh_a_daily`（新浪） | 前复权 qfq |
| ETF | `fund_etf_hist_sina`（新浪） | `fund_etf_hist_em`（东方财富） | 前复权 qfq |

### 6.2 增量更新算法

```
已有文件最后日期: last_date
今日日期: today

if last_date >= today:
    跳过（已是最新）

else:
    获取区间: (last_date + 1) ~ today
    只追加 last_date 之后的新行
    已有数据不重复写入
```

### 6.3 重试机制

| 参数 | 值 |
|------|-----|
| 触发条件 | 网络错误或接口返回空数据 |
| 等待间隔 | 120 秒（2 分钟） |
| 最大重试次数 | 3 次 |
| 重试失败处理 | 写入错误日志，继续下一只股票 |

### 6.4 代码格式转换规则

```
A股代码（纯数字6位）:
  6开头 → sh + code  (如 601318 → sh601318)
  0/2/3开头 → sz + code  (如 002001 → sz002001)

ETF代码（纯数字6位）:
  统一 → sh + code  (如 520500 → sh520500)
```

### 6.5 列名标准化

AKShare 各接口可能返回中文列名，统一映射为英文：

```
日期/交易日期 → date
开盘/开盘价   → open
最高/最高价   → high
最低/最低价   → low
收盘/收盘价   → close
成交量/成交额 → volume
```

---

## 7. 边界条件汇总

| 场景 | 最小行数要求 | ATR 预热要求 | Pivot 预热要求 | 预期行为 |
|------|------------|------------|---------------|----------|
| 正常计算 | — | — | — | 完整输出 |
| ATR 预热期 | < atr_window | ATR=NaN | — | 不形成结构 |
| Pivot 预热期 | < 2*pivot_len | — | 无 ph/pl | 不形成结构 |
| Trend 预热期 | < 4 | — | — | trend=False |
| 极短数据 | < 2*pivot_len | ATR 可能 NaN | 无信号 | signal 全为 0 |
| 空输入 | 0 行 | — | — | raise ValueError |
| 日期重复 | — | — | — | raise ValueError |
| 趋势翻转 | — | — | — | 立即清空所有结构 |

---

## 8. 错误日志格式

**指标运行错误日志**（`log/jurik_breakout_<YYYYMMDD>_error.log`）：
```
2026-04-10 14:30:01 [ERROR] indicator run failed: missing required columns: ['volume']
  Input path: data/daily_price/xxx.csv
  Indicator: jurik_breakout
  Config: {"len": 9, "phase": 0.15, ...}
```

**数据获取错误日志**（`log/dailyprice_<YYYYMMDD>_error.log`）：
```
2026-04-10 09:15:03 [ERROR] [520500] 恒生创新药ETF: 最终失败（已重试3次）- network timeout
  Stock: 520500 | Name: 恒生创新药ETF
```

---

## 9. 性能考量

- JMA 递归循环：O(n)，不可并行，但 n 为日线数据（300-500行/文件），极快
- Pivot 检测：O(n × pivot_len)，日线规模下无压力
- StateMachine 逐行：O(n)，与数据规模线性相关
- CSV I/O：使用 pandas 默认 csv writer，无额外优化需求
- Plotly HTML：大型文件（~4.7MB/股票）因包含完整交互数据，暂不优化

---

## 10. 风险与限制

| 风险 | 缓解措施 |
|------|----------|
| AKShare 接口不可用 | 自动 fallback 到备用接口 + 3次重试 + 2分钟等待 |
| ETF 接口当前失效 | 记录在 datafetch.md 已知问题中，网络修复后可启用 |
| Pandas-ta ATR 与 Pine 不完全一致 | 使用 `mamode="rma"` 确保平滑方式一致 |
| Pivot 极点并列 | 代码明确拒绝并列极值，避免误判 |
| 大文件 HTML 图表 | 暂接受规模，后续可考虑数据抽样渲染 |
