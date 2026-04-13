# A_share — 变更日志（CHANGELOG）

> 所有设计文档（A_share_SDD.md、A_share_DDS.md、A_share_Interface.md、A_share_Test_Cases.md）的变更记录。
> 版本编号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/) 规范。
> 格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [1.1.1] — 2026-04-12

### 新增
- 4 份核心设计文档及规范文档全部添加 **审批人** 字段：`SimonLiao`
- CHANGELOG.md：新增变更历史追踪文件
- docs/DOC_VERSIONING.md：新增文档版本管理规范（含同步规则、Commit 规范、检查清单）
- docs/template/：新增 4 份文档标准模板（SDD / DDS / Interface / Test Cases）

### 变更
- SDD / DDS / Interface / Test Cases：文档头部新增 `审批人：SimonLiao` 字段
- DOC_VERSIONING.md：文档清单 / 模板规范 / 维护者规则中同步纳入审批人字段

---

## [1.1.0] — 2026-04-12

### 新增

- **文档版本管理体系**
  - 新增 `docs/DOC_VERSIONING.md`：定义版本编号规则（SemVer）、同步触发规则、变更流程、Commit 规范
  - 新增 `CHANGELOG.md`：集中追踪所有文档变更历史
  - 新增 `docs/template/`：4 份文档的标准模板（含版本头、格式规范）
  - 新增 `.docignore`：文档目录的 Git 忽略规则

### 说明

- 本次为初始版本体系建立，不涉及代码变更
- 4 份核心文档版本号从 `1.0` 升至 `1.1.0`，表示新增规范体系（MINOR 升级）
- 后续所有代码变更必须同步更新对应文档，并在本文件记录

---

## [1.0.0] — 2026-04-10

### 新增

- **SDD（系统级设计）**
  - 项目整体架构、模块职责划分
  - 技术栈定义（AKShare / pandas / pandas-ta / Plotly）
  - CLI 使用方式（数据获取 + 指标计算）
  - Portfolio 配置格式
  - 扩展性设计（IndicatorEngine 注册机制）
  - 已知限制说明

- **DDS（详细设计）**
  - JMA 算法公式（含 beta/alpha 推导）
  - Trend 趋势判断逻辑
  - ATR 计算（pandas-ta RMA 模式）
  - Pivot 极点检测（唯一极值语义）
  - Breakout StateMachine 完整状态机规则
  - 端到端数据流图
  - 各模块函数签名
  - 边界条件汇总表
  - 错误日志格式规范
  - 数据获取模块 AKShare 接口映射

- **Interface（接口定义）**
  - BaseIndicator 抽象基类
  - IndicatorEngine 注册/执行机制
  - JurikBreakoutIndicator 完整接口
  - DataLoader / OutputWriter / PlotRenderer 接口
  - DataFetchCLI 所有子命令接口
  - 异常类型定义（ValueError / KeyError / RuntimeError）

- **Test Cases（测试用例）**
  - UT：JMA / ATR / Pivot / StateMachine 单元测试
  - CT：JurikBreakoutIndicator 组件测试
  - IT：端到端集成测试
  - RT：回归测试（4 只股票真实数据快照）
  - EX：边界条件测试（空数据 / ATR 预热 / 趋势翻转等）
  - 黄金验收数据快照（data/tests/ 快照 CSV）

### 初始版本

> A_share 项目首个完整设计文档集，支持 Jurik MA Trend Breakouts 指标全流程实现。

---

*本文件由 `DOC_VERSIONING.md` 规范管理。
每次代码变更后，在此文件顶部追加新的版本块，保持最新变更在前。
版本块一旦发布，禁止修改或删除。*
