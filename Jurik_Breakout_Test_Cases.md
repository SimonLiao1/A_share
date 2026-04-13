# Jurik Breakout Test Cases

## 1. Purpose

This document defines the test strategy for the Python re-implementation
of the TradingView `Jurik MA Trend Breakouts` indicator. The goal is to
verify numerical correctness, time-series causality, state-machine
behavior, and file-based integration against the current repository
layout.

## 2. Test Data Sources

### 2.1 Real CSV Files

Primary real-world inputs from `data/daily_price`:

- `data/daily_price/中国中铁_20260410.csv`
- `data/daily_price/中国平安_20260410.csv`
- `data/daily_price/紫金矿业_20260410.csv`
- `data/daily_price/新和成_20260410.csv`

Recommended usage:

- `中国中铁_20260410.csv`: main regression and integration sample because
  it contains mixed trend and consolidation periods.
- `中国平安_20260410.csv`: second regression baseline.
- `紫金矿业_20260410.csv`: useful for more volatile price swings.
- `新和成_20260410.csv`: useful for cross-symbol consistency checks.

### 2.2 Synthetic Fixtures

Small handcrafted DataFrames are still required for deterministic unit
tests because:

- ATR warm-up behavior is easier to verify.
- Pivot-delay semantics can be checked bar by bar.
- Breakout sequences can be forced without searching large files.

## 3. Test Levels

### 3.1 Unit Tests

Target scope:

- `compute_jma`
- `compute_atr`
- `detect_pivots`
- `BreakoutStateMachine.update`
- input validation helpers

Objective:

- isolate formula correctness and state transitions
- avoid dependence on file I/O or plotting

### 3.2 Component Tests

Target scope:

- `JurikBreakoutIndicator.compute`

Objective:

- verify the end-to-end indicator output for a supplied DataFrame
- ensure all required columns are present
- ensure row count and order are preserved

### 3.3 Integration Tests

Target scope:

- `load_price_data -> indicator -> csv output`

Objective:

- verify the repository's current CSV format is accepted without
  reshaping
- verify generated output can be written back to CSV

### 3.4 Regression Tests

Target scope:

- stable snapshots on selected real files

Objective:

- detect behavior changes after refactors
- compare signal counts, key event indices, and selected derived series

## 4. Test Matrix

| ID | Level | Scenario | Source | Main Assertion |
| --- | --- | --- | --- | --- |
| UT-01 | Unit | JMA initialization | synthetic | `jma[0] == close[0]` |
| UT-02 | Unit | JMA recursive update | synthetic | each bar matches recursive formula |
| UT-03 | Unit | ATR true range | synthetic | TR uses previous close correctly |
| UT-04 | Unit | ATR warm-up | synthetic | first `atr_window - 1` rows are `NaN` |
| UT-05 | Unit | Pivot high delay | synthetic | pivot at source bar appears only after `pivot_len` bars |
| UT-06 | Unit | Pivot low delay | synthetic | same for lows |
| UT-07 | Unit | Upper structure creation | synthetic | structure forms only when `abs(ph2 - ph1) < atr` |
| UT-08 | Unit | Lower structure creation | synthetic | same for support side |
| UT-09 | Unit | Trend flip reset | synthetic | active structure clears immediately |
| UT-10 | Unit | Breakout up signal | synthetic | `signal == 1` only on breakout bar |
| UT-11 | Unit | Breakout down signal | synthetic | `signal == -1` only on breakout bar |
| UT-12 | Unit | Breakout guard | synthetic | pivot before last breakout cannot recreate old structure |
| CT-01 | Component | Standard output schema | real CSV subset | required columns all exist |
| CT-02 | Component | Row preservation | real CSV subset | output row count equals input row count |
| CT-03 | Component | Signal domain | real CSV subset | signal values limited to `-1, 0, 1` |
| CT-04 | Component | No future leakage in pivots | real CSV subset | `ph_idx <= current_idx - pivot_len` and same for `pl_idx` |
| IT-01 | Integration | Load and compute on `中国中铁` | real CSV | pipeline runs without schema transform |
| IT-02 | Integration | Write result CSV | real CSV | output file includes derived columns |
| IT-03 | Integration | Optional chart generation | real CSV | chart step reads output columns only |
| IT-04 | Integration | Error log path creation | real CSV | failures are written under root `log/` |
| RT-01 | Regression | `中国中铁` snapshot | real CSV | stable event indices and signal count |
| RT-02 | Regression | `中国平安` snapshot | real CSV | stable event indices and signal count |
| RT-03 | Regression | cross-symbol smoke set | all 4 files | no exceptions and valid schema |
| EX-01 | Negative | empty CSV | synthetic | raises `ValueError` |
| EX-02 | Negative | missing `close` column | synthetic | raises `ValueError` |
| EX-03 | Negative | unsorted dates | synthetic | raises `ValueError` |
| EX-04 | Negative | null `close` values | synthetic | raises `ValueError` |
| EX-05 | Negative | too-short series | synthetic | no signal, pivots unavailable |

## 5. Detailed Unit Test Cases

### UT-01 JMA Initialization

Input:

- close series `[10.0, 11.0, 12.0]`
- `len = 3`
- `phase = 1.0`

Expected:

- `jma[0] == 10.0`

### UT-02 JMA Recursive Update

Input:

- close series `[10.0, 11.0, 12.0, 11.0]`
- fixed `len` and `phase`

Expected:

- every `jma[i]` equals `(1 - alpha) * close[i] + alpha * jma[i-1]`
- comparison should use floating tolerance

### UT-03 ATR True Range

Input:

```text
date        open  high  low  close
2026-01-01  10    11    9    10
2026-01-02  10    12    9    11
2026-01-03  11    13    8    12
```

Expected:

- day 2 true range is `max(12-9, abs(12-10), abs(9-10))`
- day 3 true range is `max(13-8, abs(13-11), abs(8-11))`

### UT-05 and UT-06 Pivot Delay

Input:

- `pivot_len = 2`
- build a series where the center bar is an obvious local max or min

Expected:

- pivot event becomes visible exactly 2 bars after the source bar
- pivot must not appear earlier

### UT-07 Upper Structure Creation

Input:

- two confirmed pivot highs in up-trend
- `abs(ph2 - ph1) < atr`

Expected:

- `structure_active == True`
- `structure_side == "upper"`
- `res_line == ph2`
- no signal before breakout

### UT-09 Trend Flip Reset

Setup:

- create an active upper structure
- then feed one row with `trend = False`

Expected:

- `structure_active == False`
- `res_line is None or NaN`
- no stale resistance carries into down-trend

### UT-10 and UT-11 Breakout Signals

Setup:

- active upper structure with `res_line = 10.5`
- feed one row with `close = 10.6`

Expected:

- `signal == 1`
- `breakout_up == True`
- active upper structure is cleared on the same row

Equivalent support-side test:

- active lower structure with `sup_line = 9.5`
- one row with `close = 9.4`
- expect `signal == -1`

## 6. Component Test Cases

### CT-01 Output Schema Completeness

Source:

- first 120 rows of `data/daily_price/中国中铁_20260410.csv`

Assertions:

- output contains all required derived columns
- original OHLCV columns still exist
- output row count equals input row count

### CT-02 Signal Domain

Source:

- same DataFrame as CT-01

Assertions:

- `set(signal.unique())` is a subset of `{-1, 0, 1}`
- `breakout_up` and `breakout_down` are boolean-like

### CT-03 Causality Check

Source:

- same DataFrame as CT-01

Assertions:

- if `ph` exists on row `i`, then `ph_idx <= i - pivot_len`
- if `pl` exists on row `i`, then `pl_idx <= i - pivot_len`
- no row writes a pivot source index from the future

## 7. Integration Test Cases

### IT-01 Real File End-to-End

Source:

- `data/daily_price/中国中铁_20260410.csv`

Flow:

1. load CSV
2. validate schema
3. run indicator with default config
4. write result CSV

Assertions:

- pipeline completes without exception
- output CSV exists
- output includes at least one of `jma`, `trend`, `signal`

### IT-02 Cross-Symbol End-to-End

Source:

- all four real CSV files

Assertions:

- each file loads under the same loader contract
- each output preserves row count
- each run produces a valid schema

### IT-03 Plot Adapter Smoke Test

Source:

- output of IT-01

Assertions:

- plot function does not recompute the indicator
- output HTML is generated when charting is enabled

### IT-04 Error Log Path

Source:

- one real CSV path
- one forced runtime failure, such as an invalid indicator config

Assertions:

- the root-level `log/` directory is created when missing
- `error_log_path` resolves under `log/`
- the generated file name follows
  `jurik_breakout_<YYYYMMDD>_error.log`
- the log records the failing input path and exception message

## 8. Regression Test Strategy

Regression tests should freeze:

- configuration used
- input CSV filename
- expected event summary

Recommended snapshot fields:

- total rows
- first and last date
- count of `pivot_confirm == True`
- count of `signal == 1`
- count of `signal == -1`
- first 10 non-null rows of `res_line`
- first 10 non-null rows of `sup_line`
- breakout row indices

Recommended real-file baselines:

- `中国中铁_20260410.csv`
- `中国平安_20260410.csv`

Regression rule:

- compare against a stored snapshot file committed to the repository
- if logic changes intentionally, snapshot must be reviewed and updated

## 9. Negative and Edge Cases

### EX-01 Empty Input

Expected:

- raise `ValueError`

### EX-02 Missing Required Columns

Examples:

- missing `close`
- missing `high`

Expected:

- raise `ValueError`

### EX-03 Unsorted Dates

Expected:

- raise `ValueError` or sort explicitly before compute, depending on the
  chosen implementation contract

Recommended contract:

- loader may sort
- indicator should still reject unsorted input passed directly

### EX-04 Null Close

Expected:

- raise `ValueError`

### EX-05 Short Input

Input:

- fewer than `2 * pivot_len + 1` rows

Expected:

- no confirmed pivots
- no active structures
- signal column remains zero

### EX-06 ATR Not Ready

Input:

- series shorter than `atr_window`

Expected:

- ATR is `NaN`
- structure formation is disabled
- breakout signals remain zero

## 10. Golden Acceptance Example

This small synthetic dataset is intended for manual verification of
state-machine timing. Use reduced parameters to keep the expected values
easy to reason about:

- `len = 3`
- `phase = 1.0`
- `pivot_len = 1`
- `atr_window = 3`

Example input:

| idx | close | high | low |
| --- | ---: | ---: | ---: |
| 0 | 10.0 | 10.2 | 9.8 |
| 1 | 10.8 | 11.0 | 10.1 |
| 2 | 10.2 | 10.4 | 9.9 |
| 3 | 10.9 | 11.1 | 10.3 |
| 4 | 10.4 | 10.5 | 10.0 |
| 5 | 11.3 | 11.5 | 10.8 |

Expected event semantics:

| idx | Expected trend | Expected pivot event | Expected structure | Expected signal |
| --- | --- | --- | --- | --- |
| 0 | warm-up | none | none | 0 |
| 1 | warm-up | none | none | 0 |
| 2 | derived from JMA | pivot-high for source idx 1 may confirm here | no structure yet, only first pivot tracked | 0 |
| 3 | derived from JMA | none | none | 0 |
| 4 | derived from JMA | pivot-high for source idx 3 may confirm here | if ATR rule passes, upper structure becomes active with `res_line = high[idx3]` | 0 |
| 5 | derived from JMA | none | upper structure should be active before price check | `1` if `close[5] > res_line` |

What this case verifies:

- pivot events appear after delay, not at the source bar
- the first pivot only initializes state
- the second pivot may create structure
- breakout happens only after structure exists

## 11. Recommended Implementation Order For Tests

1. Write unit tests for JMA, ATR, and pivot timing first.
2. Add state-machine tests using synthetic rows.
3. Add one component test on `中国中铁_20260410.csv`.
4. Add regression snapshots only after implementation is stable.
5. Add plot smoke tests last because they are lower value than signal and
   causality checks.

## 12. Pass Criteria

The implementation is considered acceptable when:

- all unit tests pass
- integration on the four real CSV files succeeds
- no causality violation is detected
- signal values remain in `{-1, 0, 1}`
- regression snapshots are stable under refactor-only changes
