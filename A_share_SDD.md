# A_share 项目 — 软件设计文档（SDD）

> **项目名称**：A_share — A 股技术分析指标系统
> **版本**：1.0
> **日期**：2026-04-10
> **作者**：Simon Liao
> **审批人**：SimonLiao

---

## 1. 目的与范围

### 1.1 项目目标

A_share 是一个面向 **A 股（含 ETF）日线数据**的**技术分析指标系统**，核心功能是：

1. **数据获取**：通过 AKShare 接口抓取 A 股历史日线数据（支持全量/增量更新）
2. **指标计算**：实现 TradingView Pine Script `Jurik MA Trend Breakouts` 指标，行为等价复现
3. **信号输出**：结构化 CSV 结果文件，包含所有中间计算列
4. **可视化**：Plotly 交互式 HTML 图表（K 线 + JMA + 结构线 + 突破信号）

### 1.2 范围边界

| 范围内 | 范围外 |
|--------|--------|
| A 股日线 CSV 数据处理 | 实时行情 / 分时数据 |
| Jurik Breakout 指标 | 其他技术指标（预留扩展） |
| Plotly HTML 图表 | TradingView 插件集成 |
| CLI 单文件执行 | Web API / 在线服务 |
| Portfolio 配置化运行 | 量化回测框架 |
| 错误日志记录 | 邮件/通知告警 |

### 1.3 参考基准

行为参考：`doc/Jurik`（TradingView Pine Script v6 源码）

---

## 2. 行为基线

### 2.1 Pine Script 等价性要求

以下 Pine 语义必须在 Python 中精确复现：

```pinescript
jSmooth = JurikMA(close, len, phase)
trend   = jSmooth >= jSmooth[3]    // barstate.isconfirmed
ph      = ta.pivothigh(pivotLen, pivotLen)
pl      = ta.pivotlow(pivotLen, pivotLen)
atr     = ta.atr(200)
```

**结构形成规则**：
- 上轨结构**仅在上涨趋势中**形成
- 下轨结构**仅在下跌趋势中**形成
- 两个极点的价差必须 **小于 ATR** 才算有效结构
- 突破信号**仅在结构存在时**发出
- 趋势翻转**立即清除**所有活跃结构

### 2.2 核心信号定义

| 信号 | 条件 | 输出值 |
|------|------|--------|
| 买入 | 收盘价向上突破上轨阻力线 | `signal = 1` |
| 卖出 | 收盘价向下突破下轨支撑线 | `signal = -1` |
| 观望 | 无结构或结构未触发 | `signal = 0` |

---

## 3. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            A_share 系统                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐ │
│  │ AKShare 接口  │───▶│ Data Fetch CLI │───▶│ data/daily_price/*.csv  │ │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘ │
│                                                         │              │
│                                                         ▼              │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                     run_indicator.py（CLI 入口）                │     │
│  │  参数解析 → 日志初始化 → 数据加载 → 指标计算 → CSV输出 → 图表渲染  │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              │                                          │
│          ┌──────────────────┼──────────────────┐                     │
│          ▼                  ▼                  ▼                       │
│  ┌────────────┐    ┌────────────────┐   ┌─────────────┐              │
│  │ DataLoader │───▶│  IndicatorCore │──▶│ StateMachine│              │
│  │  (loader)  │    │  (analytics/)  │   │(breakout.py)│              │
│  └────────────┘    └────────────────┘   └──────┬──────┘              │
│          │                   │                   │                    │
│          │                   ▼                   ▼                    │
│          │          ┌────────────────┐   ┌─────────────────┐          │
│          │          │  OutputBuilder │──▶│ ResultDataFrame │          │
│          │          └────────────────┘   └────────┬────────┘          │
│          │                                            │                 │
│          ▼                                            ▼                 │
│  ┌────────────┐                            ┌──────────────────┐       │
│  │ error.log  │                            │ Plotly HTML Chart │       │
│  │  (log/)    │                            │  output/charts/   │       │
│  └────────────┘                            └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块职责总览

| 模块 | 路径 | 职责 |
|------|------|------|
| 数据获取 | `src/data_fetch/` | AKShare 接口封装，全量/增量获取，错误重试 |
| 数据加载 | `src/io/loader.py` | CSV 读取，schema 验证，日期排序 |
| 指标核心 | `src/indicators/jurik_breakout.py` | 指标编排：JMA + ATR + Pivots + StateMachine |
| 分析算法 | `src/analytics/` | JMA、ATR、Pivot 具体实现 |
| 状态机 | `src/state_machine/breakout.py` | 极点追踪、结构形成、突破检测 |
| 输出写入 | `src/io/writer.py` | CSV 输出、文件名生成、日志路径管理 |
| 可视化 | `src/visualization/` | Plotly HTML 图表渲染 |
| CLI 入口 | `src/run_indicator.py` | 命令行参数解析、日志初始化、流程编排 |

---

## 4. 设计原则

1. **Pine 等价性优先**：所有指标算法必须与 TradingView Pine Script 行为一致，不允许擅自优化或简化
2. **时间序列因果性**：禁止使用未来信息，每一列的计算结果在时间上不可超越输入数据的最末行
3. **全量中间列暴露**：输出 DataFrame 必须包含所有中间计算列，支持逐行审计和回归测试
4. **递归显式化**：JMA 等递归算法用显式循环实现，不强行向量化（向量化会破坏递归依赖的可读性）
5. **失败即报错**：输入验证失败必须抛出 `ValueError`，不允许静默跳过
6. **图表是纯展示层**：可视化代码不得包含任何业务逻辑，不重新计算指标

---

## 5. 技术栈

| 层级 | 技术选型 | 用途 |
|------|----------|------|
| 数据获取 | akshare | A 股/ETF 历史日线 |
| 数据处理 | pandas | DataFrame 全流程 |
| 技术指标 | pandas-ta（ATR）+ 自定义（JMA/Pivot） | 指标计算 |
| 可视化 | plotly | 交互式 HTML 图表 |
| 状态管理 | 自定义类（BreakoutStateMachine） | 结构/突破状态追踪 |
| 日志 | Python logging | 控制台输出 + 错误文件 |
| 测试 | unittest | 单元/集成/回归 |
| 配置 | argparse + JSON | CLI 参数 + Portfolio 配置 |

---

## 6. 项目目录结构

```
A_share/
├── data/
│   └── daily_price/                    # A 股日线 CSV 数据
│       ├── 中国中铁_20260410.csv
│       ├── 中国平安_20260410.csv
│       ├── 新和成_20260410.csv
│       └── 紫金矿业_20260410.csv
├── doc/
│   └── Jurik                           # TradingView Pine Script 原始代码
├── log/                                # 运行时错误日志
│   ├── jurik_breakout_<YYYYMMDD>_error.log
│   └── dailyprice_<YYYYMMDD>_error.log
├── output/
│   ├── result_csv/                     # 指标计算结果
│   │   ├── 中国中铁_jurik_breakout.csv
│   │   └── ...
│   └── charts/                         # Plotly HTML 图表
│       ├── 中国中铁_jurik_breakout.html
│       └── ...
├── portfolio/
│   └── Portfolio_shares.json           # 持仓配置（代码/名称/板块）
├── src/
│   ├── __init__.py
│   ├── run_indicator.py                 # CLI 入口（指标计算）
│   ├── data_fetch/
│   │   └── astock_cli_daily_price.py   # 数据获取 CLI
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseIndicator 抽象基类
│   │   ├── engine.py                   # IndicatorEngine（注册/执行）
│   │   └── jurik_breakout.py          # JurikBreakoutIndicator 主实现
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── atr.py                      # ATR 计算（pandas-ta RMA）
│   │   ├── jma.py                      # Jurik MA + Trend
│   │   └── pivots.py                   # Pivot High/Low 检测
│   ├── state_machine/
│   │   ├── __init__.py
│   │   └── breakout.py                 # BreakoutStateMachine 状态机
│   ├── io/
│   │   ├── __init__.py
│   │   ├── loader.py                   # CSV 加载 + 验证
│   │   └── writer.py                   # CSV 输出 + 路径管理
│   └── visualization/
│       ├── __init__.py
│       └── plot_jurik_breakout.py     # Plotly 图表渲染
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_indicator_core.py     # 单元测试（JMA/ATR/Pivot/StateMachine）
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_jurik_pipeline.py    # 集成测试（CSV → 指标 → 输出）
│   └── regression/
│       ├── __init__.py
│       └── test_jurik_regression.py  # 回归测试（4只股票快照）
├── A_share_SDD.md                      # 本文档（系统级设计）
├── A_share_DDS.md                      # 详细设计文档
├── A_share_Interface.md                # 接口定义文档
├── A_share_Test_Cases.md              # 测试用例文档
├── datafetch.md                        # 数据获取工具设计文档
├── requirements.txt                    # Python 依赖
└── README.md                          # 项目说明
```

---

## 7. 运行时路径约定

| 路径类型 | 格式 | 示例 |
|----------|------|------|
| 输入 CSV | `data/daily_price/<名称>_<YYYYMMDD>.csv` | `data/daily_price/中国中铁_20260410.csv` |
| 指标结果 CSV | `output/result_csv/<名称>_jurik_breakout_result.csv` | `output/result_csv/中国中铁_jurik_breakout_result.csv` |
| 图表 HTML | `output/charts/<名称>_jurik_breakout.html` | `output/charts/中国中铁_jurik_breakout.html` |
| 指标错误日志 | `log/jurik_breakout_<YYYYMMDD>_error.log` | `log/jurik_breakout_20260410_error.log` |
| 数据获取错误日志 | `log/dailyprice_<YYYYMMDD>_error.log` | `log/dailyprice_20260410_error.log` |

---

## 8. Portfolio 配置

文件路径：`portfolio/Portfolio_shares.json`

结构：
```json
{
  "portfolios": {
    "default": {
      "name": "default",
      "description": "默认投资组合",
      "shares": [
        { "code": "002001", "name": "新和成",   "asset_class": "stock", "exchange": "SZSE", "sector": "医药化工" },
        { "code": "520500", "name": "恒生创新药ETF", "asset_class": "etf",  "exchange": "SSE", "sector": "ETF-医药" },
        { "code": "601318", "name": "中国平安", "asset_class": "stock", "exchange": "SSE", "sector": "金融-保险" },
        { "code": "601390", "name": "中国中铁", "asset_class": "stock", "exchange": "SSE", "sector": "基建-铁路" },
        { "code": "601899", "name": "紫金矿业", "asset_class": "stock", "exchange": "SSE", "sector": "矿业-黄金铜矿" }
      ]
    }
  }
}
```

---

## 9. CLI 使用方式

### 9.1 数据获取 CLI

```bash
# 查看 Portfolio 列表
python -m src.data_fetch.astock_cli_daily_price list

# 查看各标的数据状态
python -m src.data_fetch.astock_cli_daily_price status --portfolio default

# 获取/更新数据（全量或增量）
python -m src.data_fetch.astock_cli_daily_price fetch --portfolio default
```

### 9.2 指标计算 CLI

```bash
python src/run_indicator.py \
  --indicator jurik_breakout \
  --input data/daily_price/中国中铁_20260410.csv \
  --output output/中国中铁_jurik_breakout.csv \
  --chart output/charts/中国中铁_jurik_breakout.html \
  --log-dir log \
  --len 9 \
  --phase 0.15 \
  --pivot-len 4 \
  --atr-window 200
```

---

## 10. 扩展性设计

### 10.1 新增指标

通过 `IndicatorEngine` 注册新指标类：

```python
engine = IndicatorEngine()
engine.register("jurik_breakout", JurikBreakoutIndicator)
# 未来可注册：
# engine.register("macd", MACDIndicator)
# engine.register("rsi", RSIIndicator)
```

新增指标只需：
1. 继承 `BaseIndicator`
2. 实现 `compute(df) -> DataFrame`
3. 注册到 Engine

### 10.2 新增 Portfolio

在 `Portfolio_shares.json` 的 `portfolios` 下新增 key 即可：

```json
{
  "portfolios": {
    "default": { ... },
    "high_dividend": { ... }
  }
}
```

---

## 11. 已知限制

1. **Pivot 延迟**：极点检测天然滞后 `pivot_len` 根 K 线
2. **ATR 预热期**：前 `atr_window - 1` 行 ATR 为 `NaN`，此期间不形成结构
3. **ETF 接口**：当前网络环境无法访问 ETF 新浪/东财接口，ETF 暂时无法获取
4. **无回测框架**：当前不包含量化回测功能（预留接口）
5. **Pine 线条差异**：Python 实现存储结构价位为数据列，不含 Pine 中的辅助连接线

---

## 12. 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-04-10 | 1.0 | 初始版本，支持 Jurik Breakout 指标 + AKShare 数据获取 |
