#!/usr/bin/env python3
"""
A-Share Stock Daily Price Fetcher CLI
======================================
从 AKShare 获取 A 股（含 ETF）历史日线数据，
支持全量获取和增量更新，数据存储为 CSV 文件。

用法：
    python astock_cli_daily_price.py fetch [--portfolio NAME]
    python astock_cli_daily_price.py status [--portfolio NAME]
    python astock_cli_daily_price.py list
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ─── 全局路径配置 ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path("/root/stock/A_share")
PORTFOLIO_FILE = PROJECT_ROOT / "portfolio" / "Portfolio_shares.json"
DATA_DIR = PROJECT_ROOT / "data" / "daily_price"
LOG_DIR = PROJECT_ROOT / "log"
SRC_DIR = PROJECT_ROOT / "src" / "data_fetch"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ─── 日志配置 ────────────────────────────────────────────────────────────────
def get_error_log_path():
    today = datetime.now().strftime("%Y%m%d")
    return LOG_DIR / f"dailyprice_{today}_error.log"

def setup_logger():
    logger = logging.getLogger("astock_daily_price")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # 控制台 handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # 错误文件 handler
    error_log_path = get_error_log_path()
    fh = logging.FileHandler(error_log_path, encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s\n"
        "  Stock: %(stock_code)s | Name: %(stock_name)s\n",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    class StockContextFilter(logging.Filter):
        def filter(self, record):
            record.stock_code = getattr(record, "stock_code", "-")
            record.stock_name = getattr(record, "stock_name", "-")
            return True

    fh.addFilter(StockContextFilter())
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

logger = setup_logger()

# ─── AKShare 导入 ────────────────────────────────────────────────────────────
try:
    import akshare as ak
    import pandas as pd
except ImportError as e:
    logger.error(f"akshare 或 pandas 未安装: {e}")
    logger.error("请执行: pip install akshare pandas --break-system-packages")
    sys.exit(1)


# ─── 常量 ───────────────────────────────────────────────────────────────────
START_DATE = "20250101"
RETRIES = 3
RETRY_WAIT = 120  # 秒


# ─── 工具函数 ────────────────────────────────────────────────────────────────

def load_portfolio(name: str = "default") -> dict:
    if not PORTFOLIO_FILE.exists():
        raise FileNotFoundError(f"Portfolio 文件不存在: {PORTFOLIO_FILE}")
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    portfolios = data.get("portfolios", {})
    if name not in portfolios:
        raise ValueError(f"Portfolio '{name}' 不存在，可用: {list(portfolios.keys())}")
    return portfolios[name]


def list_portfolios() -> list:
    if not PORTFOLIO_FILE.exists():
        return []
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("portfolios", {}).keys())


def get_existing_data_file(stock_name: str) -> Path | None:
    """查找已有的日线数据文件，取最新日期的文件。"""
    pattern = f"{stock_name}_*.csv"
    files = list(DATA_DIR.glob(pattern))
    if not files:
        return None
    files.sort(key=lambda f: f.name, reverse=True)
    return files[0]


def get_last_date_from_file(filepath: Path) -> datetime | None:
    """读取 CSV 最后一行的日期"""
    try:
        df = pd.read_csv(filepath)
        if df.empty:
            return None
        return pd.to_datetime(df["date"].iloc[-1])
    except Exception:
        return None


def build_filename(stock_name: str) -> str:
    """生成今日文件命名：<name>_YYYYMMDD.csv"""
    today = datetime.now().strftime("%Y%m%d")
    safe_name = "".join(c for c in stock_name if c.isalnum() or c in ("_", "-"))
    return f"{safe_name}_{today}.csv"


def to_csv_filepath(stock_name: str) -> Path:
    return DATA_DIR / build_filename(stock_name)


def get_today_str() -> str:
    return datetime.now().strftime("%Y%m%d")


def to_trade_date(date_str: str) -> str:
    """将 YYYYMMDD 转为 YYYY-MM-DD"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


# ─── 股票代码格式转换 ────────────────────────────────────────────────────────

def make_akshare_symbol(code: str, asset_class: str = "stock") -> str:
    """
    将 Portfolio 中的纯代码转为 AKShare 接口需要的格式。
    A股: 6位纯数字 → 'sh600318' 或 'sz002001'
         根据 exchange 字段判断: SSE->sh, SZSE->sz
    ETF: 6位纯数字 → 'sh520500'（新浪格式）
    """
    if asset_class == "etf":
        return f"sh{code}"  # ETF 用上证 prefix
    # 股票根据 exchange 判断
    # 这里直接根据代码规则判断：6开头->sh，0/2/3开头->sz
    if code.startswith(("6", "9")):
        return f"sh{code}"
    else:
        return f"sz{code}"


# ─── 数据获取函数 ────────────────────────────────────────────────────────────

def fetch_stock_daily(symbol: str, start_date: str, end_date: str,
                      stock_name: str, asset_class: str = "stock") -> pd.DataFrame | None:
    """
    获取单只股票/ETF 的日线数据。
    优先用主接口，失败后 fallback 到备用接口。
    """
    extra = {"stock_code": symbol, "stock_name": stock_name}

    # 转换日期格式
    start_dt = to_trade_date(start_date)
    end_dt = to_trade_date(end_date)
    start_dt_parsed = pd.to_datetime(start_dt)
    end_dt_parsed = pd.to_datetime(end_dt)

    df = None

    def _col_rename(df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名：处理中英文列名"""
        rename_map = {
            '日期': 'date', '交易日期': 'date',
            '开盘': 'open', '开盘价': 'open',
            '最高': 'high', '最高价': 'high',
            '最低': 'low', '最低价': 'low',
            '收盘': 'close', '收盘价': 'close',
            '成交量': 'volume', '成交额': 'volume',
        }
        existing = {c.strip(): c for c in df.columns}
        for cn, en in rename_map.items():
            if cn in existing:
                df = df.rename(columns={existing[cn]: en})
        return df

    if asset_class == "etf":
        # ETF: fund_etf_hist_sina (返回全部历史数据，不支持 start/end date 参数)
        try:
            logger.debug(f"[{symbol}] ETF 主接口尝试", extra=extra)
            df = ak.fund_etf_hist_sina(symbol=f"sh{symbol}")
            # 转换为日期格式并按范围过滤
            if df is not None and not df.empty and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df[(df["date"] >= start_dt_parsed) & (df["date"] <= end_dt_parsed)].copy()
        except Exception as e:
            logger.debug(f"[{symbol}] ETF 主接口失败: {e}", extra=extra)
            df = None
    else:
        # A股: 优先 stock_zh_a_hist（东方财富），失败后用 stock_zh_a_daily（新浪）
        try:
            logger.debug(f"[{symbol}] A股主接口尝试", extra=extra)
            df = ak.stock_zh_a_hist(
                symbol=symbol.lstrip("shsz"),
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
        except Exception as e:
            logger.debug(f"[{symbol}] A股主接口失败，尝试备用: {e}", extra=extra)
            df = None

        if df is None or df.empty:
            try:
                akshare_sym = make_akshare_symbol(symbol.lstrip("shsz"), asset_class)
                raw = ak.stock_zh_a_daily(symbol=akshare_sym, adjust="qfq")
                raw["date"] = pd.to_datetime(raw["date"])
                start_dt_parsed = pd.to_datetime(start_dt)
                end_dt_parsed = pd.to_datetime(end_dt)
                df = raw[(raw["date"] >= start_dt_parsed) & (raw["date"] <= end_dt_parsed)].copy()
            except Exception as e2:
                logger.debug(f"[{symbol}] A股备用接口也失败: {e2}", extra=extra)
                df = None

    if df is None or df.empty:
        # 返回空 DataFrame（而非 None）—— 调用方通过 .empty 判断
        logger.debug(f"[{symbol}] {stock_name}: 接口返回空数据", extra=extra)
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    # 标准化列名
    df = _col_rename(df)

    if df is None or df.empty:
        logger.debug(f"[{symbol}] {stock_name}: 列标准化后为空", extra=extra)
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    # 统一保留列
    keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()

    if "date" not in df.columns or "close" not in df.columns:
        logger.error(f"[{symbol}] {stock_name}: 缺少必需列 {list(df.columns)}", extra=extra)
        return None

    # 格式化日期
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # 转数值
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date", "close"]).reset_index(drop=True)

    if df.empty:
        return None

    logger.info(
        f"[{symbol}] {stock_name}: 获取 {len(df)} 条 "
        f"({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})",
        extra=extra
    )
    return df


def write_incremental(df_new: pd.DataFrame, stock_name: str) -> int:
    """
    增量写入：
    - 无文件：直接写入
    - 有文件：只追加 last_date 之后的新行
    返回追加行数。
    """
    filepath = to_csv_filepath(stock_name)
    extra = {"stock_code": "-", "stock_name": stock_name}

    if filepath.exists():
        try:
            df_existing = pd.read_csv(filepath, parse_dates=["date"])
            last_date = pd.to_datetime(df_existing["date"]).max()
            df_new = df_new[df_new["date"] > last_date.strftime("%Y-%m-%d")].copy()
            if df_new.empty:
                logger.info(f"[{stock_name}]: 数据已是最新（最后 {last_date.date()}）", extra=extra)
                return 0
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            logger.info(f"[{stock_name}]: 增量 {len(df_new)} 行，全文件共 {len(df_combined)} 行", extra=extra)
        except Exception as e:
            logger.warning(f"[{stock_name}]: 读取已有文件失败，将覆盖 - {e}", extra=extra)
            df_combined = df_new
    else:
        df_combined = df_new
        logger.info(f"[{stock_name}]: 全量写入 {len(df_combined)} 行（新文件）", extra=extra)

    df_combined.to_csv(filepath, index=False, encoding="utf-8")
    return len(df_new)


# ─── 主命令 ─────────────────────────────────────────────────────────────────

def cmd_fetch(portfolio_name: str = "default"):
    today_str = get_today_str()
    logger.info(
        f"========== 开始获取 | Portfolio: {portfolio_name} | "
        f"日期范围: {START_DATE} ~ {today_str} =========="
    )

    portfolio = load_portfolio(portfolio_name)
    shares = portfolio.get("shares", [])
    if not shares:
        logger.error(f"Portfolio '{portfolio_name}' 中无股票")
        return

    results = {"success": 0, "skipped": 0, "failed": 0}

    for share in shares:
        symbol = share.get("code", "").strip()
        name = share.get("name", "").strip()
        asset_class = share.get("asset_class", "stock")
        if not symbol or not name:
            continue

        extra = {"stock_code": symbol, "stock_name": name}
        logger.info(f"----- 处理: {name} ({symbol}) -----", extra=extra)

        # 确定起始日期
        existing_file = get_existing_data_file(name)
        if existing_file:
            last_date = get_last_date_from_file(existing_file)
            if last_date:
                start_date = (last_date + timedelta(days=1)).strftime("%Y%m%d")
                if start_date > today_str:
                    logger.info(f"[{name}]: 已是最新 (最后 {last_date.date()})", extra=extra)
                    results["skipped"] += 1
                    continue
                mode = "增量"
            else:
                start_date = START_DATE
                mode = "全量"
        else:
            start_date = START_DATE
            mode = "全量"

        is_incremental = (mode == "增量")

        # 带重试的数据获取
        df = None
        last_err = None
        already_up_to_date = False
        for attempt in range(1, RETRIES + 1):
            try:
                df = fetch_stock_daily(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=today_str,
                    stock_name=name,
                    asset_class=asset_class
                )
                if df is not None and not df.empty:
                    break
                # 增量获取返回空：说明没有新数据（市场未开/周末），无需重试
                if is_incremental and df is not None and df.empty:
                    logger.info(f"[{name}]: 已是最新 (最后 {start_date} 前无新数据)", extra=extra)
                    already_up_to_date = True
                    break
            except Exception as e:
                last_err = e
                logger.error(
                    f"[{name}] 第 {attempt}/{RETRIES} 次失败: {e}",
                    extra=extra
                )

            if attempt < RETRIES:
                logger.warning(f"[{name}] {RETRY_WAIT}秒后第 {attempt+1} 次重试...", extra=extra)
                time.sleep(RETRY_WAIT)

        if already_up_to_date:
            results["skipped"] += 1
            continue

        # 写入
        if df is not None and not df.empty:
            n = write_incremental(df, name)
            if n >= 0:
                results["success"] += 1
        else:
            err_msg = str(last_err) if last_err else "全部接口无数据"
            logger.error(
                f"[{name}]: 最终失败（已重试 {RETRIES} 次）- {err_msg}",
                extra=extra
            )
            results["failed"] += 1

    logger.info(
        f"========== 完成 | 成功: {results['success']} | "
        f"已是最新: {results['skipped']} | 失败: {results['failed']} =========="
    )


def cmd_status(portfolio_name: str = "default"):
    portfolio = load_portfolio(portfolio_name)
    shares = portfolio.get("shares", [])

    print(f"\n{'='*65}")
    print(f"  Portfolio: {portfolio_name}  |  数据状态")
    print(f"{'='*65}")
    print(f"  {'名称':<18} {'代码':<10} {'最新数据日期':<14} {'文件路径'}")
    print(f"  {'-'*65}")

    for share in shares:
        name = share.get("name", "").strip()
        symbol = share.get("code", "").strip()
        fpath = get_existing_data_file(name)

        if fpath and fpath.exists():
            last_date = get_last_date_from_file(fpath)
            last_str = last_date.strftime("%Y-%m-%d") if last_date else "未知"
            print(f"  {name:<18} {symbol:<10} {last_str:<14} {fpath.name}")
        else:
            print(f"  {name:<18} {symbol:<10} {'暂无数据':<14}  -")

    print(f"{'='*65}\n")


def cmd_list():
    portfolios = list_portfolios()
    print(f"\n可用 Portfolio: {portfolios}\n")


# ─── CLI 入口 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="A 股 / ETF 日线数据获取工具（AKShare）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python astock_cli_daily_price.py list
  python astock_cli_daily_price.py status --portfolio default
  python astock_cli_daily_price.py fetch --portfolio default
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    fetch_p = subparsers.add_parser("fetch", help="获取日线数据（增量/全量）")
    fetch_p.add_argument("-p", "--portfolio", default="default",
                        help="Portfolio 名称（默认: default）")

    status_p = subparsers.add_parser("status", help="查看各标的最新数据日期")
    status_p.add_argument("-p", "--portfolio", default="default",
                         help="Portfolio 名称（默认: default）")

    subparsers.add_parser("list", help="列出所有 Portfolio")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args.portfolio)
    elif args.command == "status":
        cmd_status(args.portfolio)
    elif args.command == "list":
        cmd_list()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
