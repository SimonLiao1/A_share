# A 股日线数据获取工具设计文档

> 本工具从 AKShare 获取 A 股（含 ETF）历史日线数据，支持全量获取和增量更新。

---

## 目录结构

```
/root/stock/A_share/
├── portfolio/
│   └── Portfolio_shares.json          # 组合配置
├── src/
│   ├── data_fetch/
│   │   └── astock_cli_daily_price.py  # CLI 主程序
│   └── strategy/                      # 后续策略目录（待扩展）
├── data/
│   └── daily_price/                   # 日线数据存储
│       ├── 新和成_20260410.csv
│       ├── 中国平安_20260410.csv
│       ├── 中国中铁_20260410.csv
│       └── 紫金矿业_20260410.csv
├── log/                               # 日志目录
│   └── dailyprice_<YYYYMMDD>_error.log
└── datafetch.md                       # 本设计文档
```

---

## CLI 命令

```bash
# 获取数据（自动识别全量/增量）
python -m astock_cli_daily_price fetch --portfolio default

# 查看各标的数据状态
python -m astock_cli_daily_price status --portfolio default

# 列出所有 Portfolio
python -m astock_cli_daily_price list
```

> 注：需要在 `/root/stock/A_share` 目录下执行，或设置 `PYTHONPATH=/root/stock/A_share/src/data_fetch`

---

## 数据接口

| 类型 | 主接口 | 备用接口 | 备注 |
|------|--------|----------|------|
| A股股票 | `stock_zh_a_hist`（东方财富） | `stock_zh_a_daily`（新浪） | 自动 fallback |
| ETF | `fund_etf_hist_sina`（新浪） | `fund_etf_hist_em`（东方财富） | 自动 fallback |

- **数据延迟**：历史日线 T+1 更新（收盘后次日可用）
- **复权方式**：前复权（qfq）
- **数据字段**：`date, open, high, low, close, volume`

---

## 增量更新逻辑

```
已有文件最后日期：2026-04-10
今天日期：2026-04-10
→ 检测到已是最新，跳过，写入 0 行
```

```
已有文件最后日期：2026-04-01
今天日期：2026-04-10
→ 增量获取：2026-04-02 ~ 2026-04-10
→ 只追加 2026-04-02 之后的新行
→ 已有日期的数据不会重复写入
```

---

## 重试机制

- **触发条件**：网络错误 / 接口返回空数据
- **等待时间**：每次失败后等待 **120 秒**（2分钟）
- **最大重试**：**3 次**
- **重试失败**：写入 `log/dailyprice_<YYYYMMDD>_error.log`，继续处理下一只股票

---

## 文件命名规则

```
<股票名称>_<YYYYMMDD>.csv
```

- `name`：来自 `Portfolio_shares.json` 中的 `name` 字段
- `YYYYMMDD`：脚本运行时的日期（北京时间）
- 示例：`新和成_20260410.csv`、`紫金矿业_20260410.csv`

---

## CSV 格式

```csv
date,open,high,low,close,volume
2025-01-02,21.07,21.56,20.60,20.68,650000.0
2025-01-03,20.68,21.20,20.55,20.76,720000.0
...
```

---

## Portfolio 配置

文件路径：`/root/stock/A_share/portfolio/Portfolio_shares.json`

```json
{
  "portfolios": {
    "default": {
      "name": "default",
      "description": "默认投资组合",
      "shares": [
        { "code": "002001", "name": "新和成", "asset_class": "stock", "exchange": "SZSE", "sector": "医药化工" },
        { "code": "520500", "name": "恒生创新药ETF", "asset_class": "etf", "exchange": "SSE", "sector": "ETF-医药" },
        { "code": "601318", "name": "中国平安", "asset_class": "stock", "exchange": "SSE", "sector": "金融-保险" },
        { "code": "601390", "name": "中国中铁", "asset_class": "stock", "exchange": "SSE", "sector": "基建-铁路" },
        { "code": "601899", "name": "紫金矿业", "asset_class": "stock", "exchange": "SSE", "sector": "矿业-黄金铜矿" }
      ]
    }
  }
}
```

---

## 已知问题

- **ETF 接口**：当前服务器网络环境无法访问 ETF 新浪/东财接口，ETF（520500 恒生创新药ETF）暂时无法获取。股票接口（A股）正常。
- **网络要求**：需要能够访问东方财富（eastmoney.com）和新浪财经（sina.com.cn）接口。

---

## 更新日志

- **2026-04-10**：初版实现，支持全量/增量获取、重试机制、错误日志
- 支持 A 股（`stock_zh_a_hist` + `stock_zh_a_daily` fallback）
- ETF 接口预留（待网络环境修复后可用）
