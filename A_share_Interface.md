# A_share 项目 — 接口定义文档（Interface）

> **项目名称**：A_share — A 股技术分析指标系统
> **版本**：1.0
> **日期**：2026-04-10
> **审批人**：SimonLiao

---

## 1. 目的

本文档定义 A_share 项目所有 Python 公开接口（类、函数）的合同规范，包括：入参类型、返回值类型、异常处理和调用约束。供开发者扩展新指标或集成到其他系统时参考。

---

## 2. 核心类接口

### 2.1 `BaseIndicator`

**文件**：`src/indicators/base.py`

所有指标的抽象基类。

```python
class BaseIndicator:
    def __init__(self, config: dict | None = None) -> None:
        """
        参数：
            config: 指标参数字典，键为 str，值为 int/float/bool。
                    可为 None，使用默认配置。
        """

    def validate_config(self) -> None:
        """
        验证配置参数的有效性。
        失败：raise ValueError
        """

    def compute(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """
        在 DataFrame 上计算指标。
        参数：
            df: 包含 ['date', 'open', 'high', 'low', 'close', 'volume'] 列的 DataFrame
                - date 须可解析为 pandas datetime
                - close 不得包含空值
                - 行须按 date 升序排列
        返回：
            新的 DataFrame，包含原始列 + 所有派生列（不修改原始 df）
        异常：
            ValueError: 配置无效或输入数据不符合前置条件
        """
        raise NotImplementedError
```

### 2.2 `JurikBreakoutIndicator`

**文件**：`src/indicators/jurik_breakout.py`

```python
class JurikBreakoutIndicator(BaseIndicator):
    DEFAULT_CONFIG = {
        "len": 9,          # JMA 长度，> 0
        "phase": 0.15,    # JMA 相位，> 0
        "pivot_len": 4,   # 极点周期，>= 1
        "atr_window": 200, # ATR 窗口，>= 1
    }

    def validate_config(self) -> None:
        """
        验证规则：
            - len > 0
            - phase > 0
            - pivot_len >= 1
            - atr_window >= 1
        """

    def compute(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """
        完整输出列（除原始列外）：
            jma, trend, atr
            ph, pl, ph_idx, pl_idx
            pivot_confirm, pivot_type
            res_line, sup_line
            res_line_start_idx, res_line_end_idx
            sup_line_start_idx, sup_line_end_idx
            structure_active, structure_side
            structure_event, structure_event_side
            structure_event_pivot1_idx, structure_event_pivot1_price
            structure_event_pivot2_idx, structure_event_pivot2_price
            signal, breakout_up, breakout_down, breakout_level, jma_glow
        """
```

### 2.3 `BreakoutStateMachine`

**文件**：`src/state_machine/breakout.py`

```python
class BreakoutStateMachine:
    def __init__(self, pivot_len: int) -> None:
        """
        参数：
            pivot_len: 极点周期，必须 >= 1
        异常：
            ValueError: pivot_len < 1
        """

    def reset(self) -> None:
        """
        重置所有状态变量：
            H, Hi, L, Li → None / -1
            BreakUp, BreakDn → 0
            upper_active, lower_active → False
            res_line_value, sup_line_value → None
            所有极点记录 → None
        """

    def update(self, idx: int, row: dict) -> dict:
        """
        处理一行数据，更新状态，返回该行的状态字典。

        参数：
            idx: 当前行在 DataFrame 中的整数索引
            row: 包含以下键的字典：
                 - close: float
                 - trend: bool
                 - atr: float | None
                 - ph:   float | None
                 - pl:   float | None
                 - ph_idx: int | None
                 - pl_idx: int | None

        返回字典：
            {
                "res_line": float | None,
                "sup_line": float | None,
                "res_line_start_idx": int | None,
                "res_line_end_idx":   int | None,
                "sup_line_start_idx": int | None,
                "sup_line_end_idx":   int | None,
                "structure_active": bool,
                "structure_side": str | None,   # "upper" | "lower" | None
                "structure_event": bool,
                "structure_event_side": str | None,
                "structure_event_pivot1_idx": int | None,
                "structure_event_pivot1_price": float | None,
                "structure_event_pivot2_idx": int | None,
                "structure_event_pivot2_price": float | None,
                "signal": int,           # -1, 0, 1
                "breakout_up": bool,
                "breakout_down": bool,
            }

        调用约束：
            - 必须按升序索引逐行调用
            - 不得跨行跳跃调用
        """
```

### 2.4 `IndicatorEngine`

**文件**：`src/indicators/engine.py`

```python
class IndicatorEngine:
    def __init__(self) -> None:
        self._registry: dict[str, type[BaseIndicator]] = {}

    def register(self, name: str, indicator_cls: type[BaseIndicator]) -> None:
        """
        注册一个指标类。
        参数：
            name: 指标名称标识符，如 "jurik_breakout"
            indicator_cls: BaseIndicator 的子类
        异常：
            ValueError: 名称已被注册
        """

    def run(self, name: str, df: "pd.DataFrame",
            config: dict | None = None) -> "pd.DataFrame":
        """
        运行已注册的指标。
        参数：
            name: 已注册的指标名称
            df: 输入 DataFrame
            config: 可选参数字典，会与 DEFAULT_CONFIG 合并
        返回：
            指标输出 DataFrame
        异常：
            KeyError: name 未注册
            ValueError: 指标 compute() 内部验证失败
        """
```

---

## 3. 辅助函数接口

### 3.1 数据加载

**文件**：`src/io/loader.py`

```python
REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

def validate_ohlcv_schema(
    df: "pd.DataFrame",
    require_sorted: bool = True
) -> None:
    """
    验证 DataFrame 是否符合 OHLCV 规范。
    异常：ValueError（任一检查项失败）

    检查项：
        1. 包含所有必需列
        2. 非空
        3. close 列无空值
        4. 日期列升序（若 require_sorted=True）
        5. 日期列无重复（若 require_sorted=True）
    """

def load_price_data(path: str | Path) -> "pd.DataFrame":
    """
    读取 CSV 文件并返回规范化的 DataFrame。
    参数：
        path: CSV 文件路径
    返回：
        规范化的 DataFrame（日期排序，数值类型）
    异常：
        FileNotFoundError: 文件不存在
        ValueError: 数据不符合 OHLCV 规范
    """
```

### 3.2 数据写入与路径

**文件**：`src/io/writer.py`

```python
def get_project_root() -> Path:
    """
    返回项目根目录（A_share/ 的绝对路径）。
    """

def ensure_directory(path: str | Path) -> Path:
    """
    确保目录存在（不存在则创建）。
    返回目录 Path 对象。
    """

def generate_output_filename(symbol: str, indicator: str) -> str:
    """
    生成结果 CSV 文件名。
    示例：
        generate_output_filename("中国中铁", "jurik_breakout")
        # → "中国中铁_jurik_breakout_result.csv"
    """

def get_error_log_path(
    indicator_name: str,
    log_dir: str = "log"
) -> Path:
    """
    返回错误日志路径。
    文件名格式：<indicator_name>_<YYYYMMDD>_error.log
    自动创建 log_dir 目录。
    示例：
        get_error_log_path("jurik_breakout")
        # → Path("log/jurik_breakout_20260410_error.log")
    """

def write_output_csv(
    df: "pd.DataFrame",
    output_path: str | Path
) -> Path:
    """
    将 DataFrame 写入 CSV 文件（utf-8 编码）。
    自动创建父目录。
    返回输出文件 Path 对象。
    """
```

### 3.3 分析算法

**文件**：`src/analytics/jma.py`

```python
def compute_jma(
    close: "pd.Series",
    length: int,
    phase: float
) -> "pd.Series":
    """
    计算 Jurik 移动平均线。
    参数：
        close: 收盘价序列
        length: JMA 长度，> 0
        phase: JMA 相位，> 0
    返回：
        JMA 值序列（与输入等长）
    异常：
        ValueError: length <= 0 或 phase <= 0 或 close 为空
    """

def derive_trend(jma: "pd.Series", lag: int = 3) -> "pd.Series":
    """
    从 JMA 推导趋势方向。
    逻辑：trend[i] = jma[i] >= jma[i-lag]
    前 lag 行固定为 False。
    异常：
        ValueError: lag <= 0
    """
```

**文件**：`src/analytics/atr.py`

```python
def compute_atr(df: "pd.DataFrame", window: int = 200) -> "pd.Series":
    """
    计算平均真实波幅（ATR）。
    使用 pandas-ta RMA 平滑，与 Pine ta.atr 等价。
    参数：
        df: 包含 high, low, close 列的 DataFrame
        window: ATR 窗口，> 0
    返回：
        ATR 序列（前 window-1 行为 NaN）
    异常：
        ValueError: window <= 0
    """
```

**文件**：`src/analytics/pivots.py`

```python
def detect_pivots(df: "pd.DataFrame", pivot_len: int) -> "pd.DataFrame":
    """
    检测 Pine 风格的极点（延迟确认语义）。
    参数：
        df: 包含 high, low 列的 DataFrame
        pivot_len: 极点周期，>= 1
    返回 DataFrame 列：
        ph, pl: float | None（极点价格）
        ph_idx, pl_idx: int | None（极点所属行索引）
        pivot_confirm: bool
        pivot_type: "high" | "low" | None
    异常：
        ValueError: pivot_len < 1
    """
```

### 3.4 可视化

**文件**：`src/visualization/plot_jurik_breakout.py`

```python
def plot_jurik_breakout(
    df: "pd.DataFrame",
    output_file: str,
    show: bool = False
) -> None:
    """
    渲染 Jurik Breakout 指标的 Plotly HTML 图表。
    参数：
        df: 指标输出 DataFrame（来自 JurikBreakoutIndicator.compute）
        output_file: HTML 输出文件路径
        show: 是否在浏览器中显示图表
    依赖：
        需要 plotly 库
    异常：
        RuntimeError: plotly 未安装
        FileNotFoundError: 输出目录不存在（父目录不存在时）
    """
```

---

## 4. CLI 接口

### 4.1 指标计算 CLI

**文件**：`src/run_indicator.py`

```bash
python src/run_indicator.py \
  --indicator <name>           # 指标名称（默认: jurik_breakout）
  --input <path>               # 输入 CSV 路径（必需）
  --output <path>              # 输出 CSV 路径（可选，自动生成）
  --chart <path>               # HTML 图表路径（可选）
  --log-dir <dir>              # 日志目录（默认: log）
  --len <int>                 # JMA 长度（默认: 9）
  --phase <float>             # JMA 相位（默认: 0.15）
  --pivot-len <int>           # Pivot 周期（默认: 4）
  --atr-window <int>          # ATR 窗口（默认: 200）
  --show-chart                # 生成图表后显示（默认: False）
```

返回值：
- `0`：执行成功
- `1`：执行失败（错误写入 `log/` 下的错误日志文件）

### 4.2 数据获取 CLI

**文件**：`src/data_fetch/astock_cli_daily_price.py`

```bash
# 获取/更新数据
python -m src.data_fetch.astock_cli_daily_price fetch --portfolio <name>

# 查看数据状态
python -m src.data_fetch.astock_cli_daily_price status --portfolio <name>

# 列出 Portfolio
python -m src.data_fetch.astock_cli_daily_price list
```

子命令：
| 命令 | 说明 | 异常处理 |
|------|------|----------|
| `fetch` | 全量或增量获取数据 | 失败写入错误日志，继续下一只 |
| `status` | 显示各标的数据最新日期 | Portfolio 不存在时退出 |
| `list` | 列出所有 Portfolio | — |

---

## 5. Portfolio 配置接口

**文件**：`portfolio/Portfolio_shares.json`

```json
{
  "portfolios": {
    "<portfolio_name>": {
      "name": "<display_name>",
      "description": "<description>",
      "shares": [
        {
          "code": "<stock_code>",       // 6位纯数字，如 "002001"
          "name": "<stock_name>",        // 中文名称，如 "新和成"
          "asset_class": "stock | etf",  // 资产类型
          "exchange": "SSE | SZSE",      // 交易所
          "sector": "<sector_name>"      // 所属板块
        }
      ]
    }
  }
}
```

股票数量：无限制
Portfolio 数量：无限制

---

## 6. 异常类型汇总

| 异常类型 | 触发场景 | 来源模块 |
|----------|----------|----------|
| `ValueError` | 配置参数无效（len<=0, phase<=0 等） | indicators, analytics |
| `ValueError` | 输入数据不符合 OHLCV 规范 | io/loader |
| `ValueError` | 指标名称重复注册 | indicators/engine |
| `KeyError` | 指标名称未注册 | indicators/engine |
| `FileNotFoundError` | CSV 文件不存在 | io/loader |
| `RuntimeError` | plotly 未安装 | visualization |
| `SystemExit(1)` | CLI 执行失败 | run_indicator.py |

---

## 7. 扩展指南

### 7.1 新增指标步骤

1. 创建 `src/indicators/<my_indicator>.py`，继承 `BaseIndicator`
2. 实现 `validate_config()` 和 `compute(df)`
3. 注册到 `IndicatorEngine`：

```python
from src.indicators.engine import IndicatorEngine
from src.indicators.jurik_breakout import JurikBreakoutIndicator

engine = IndicatorEngine()
engine.register("jurik_breakout", JurikBreakoutIndicator)
# 新增：
from src.indicators.my_indicator import MyIndicator
engine.register("my_indicator", MyIndicator)
```

### 7.2 新增 Portfolio 步骤

1. 编辑 `portfolio/Portfolio_shares.json`
2. 在 `portfolios` 下新增一个 key
3. 使用 CLI 时传入 `--portfolio <new_name>`

### 7.3 替换分析算法

如需替换 ATR 实现：
```python
# src/analytics/atr.py
# 将 ta.atr() 替换为自定义实现
# 确保返回 Series 长度与 df 一致，前 window-1 行 NaN
```
