# A_share — 文档版本管理规范（DOC_VERSIONING）

> **文件名**：DOC_VERSIONING.md
> **版本**：1.0
> **日期**：2026-04-12
> **用途**：定义 A_share 项目设计文档的版本控制规则，同步协议和变更管理流程

---

## 1. 文档资产清单

本文档管理以下 4 份核心设计文档（**SBP：Single Source of Project Truth**）：

| 文档 | 文件名 | 职责 | 版本文件 | 审批人 |
|------|--------|------|----------|--------|
| 系统级设计 | `A_share_SDD.md` | 架构、模块、技术栈、CLI、扩展性 | 独立版本号在文档头部 | SimonLiao |
| 详细设计 | `A_share_DDS.md` | 算法公式、状态机、数据流、边界条件 | 独立版本号在文档头部 | SimonLiao |
| 接口定义 | `A_share_Interface.md` | 类/函数签名、入参、异常、扩展指南 | 独立版本号在文档头部 | SimonLiao |
| 测试用例 | `A_share_Test_Cases.md` | UT/CT/IT/RT/EX 用例、输入输出断言 | 独立版本号在文档头部 | SimonLiao |

> **附加文档**（不强制版本化管理，但随项目同步维护）：
> `doc/Jurik/*.md`、`datafetch.md`、`Jurik_Breakout_*.md`

---

## 2. 版本编号规则（Semantic Versioning）

### 2.1 版本格式

```
主版本.次版本.补丁版本  （MAJOR.MINOR.PATCH）
例如：1.0.0 → 1.1.0 → 1.1.1 → 2.0.0
```

### 2.2 升级规则

| 级别 | 触发条件 | 示例 |
|------|----------|------|
| **PATCH** (`x.x.1`) | 文档文字修正、错别字修复、格式调整、注释补全，不影响代码实现 | "JMA 公式中 beta 系数说明补充" |
| **MINOR** (`x.1.0`) | 新增功能/指标/模块；新增输出列；新增测试用例；新增 API 接口；已知限制更新；注释完善但不影响算法 | "新增 Portfolio 配置支持多组合"、"新增 RSI 指标" |
| **MAJOR** (`1.0.0→2.0.0`) | 核心算法变更；接口不兼容变更；新增/删除核心模块；目录结构重组；设计原则变更 | "JMA 算法从递归改为向量化"、"删除 StateMachine 模块" |

### 2.3 版本同步原则

- 4 份文档**同步升级**版本号（同一变更同时影响多个文档时）。
- 若变更仅影响某一份文档，可以单独升级该文档版本，其他文档版本不变。
- 任何版本升级都**必须在 `CHANGELOG.md` 中记录**。

---

## 3. 同步触发规则

### 3.1 必须更新文档的场景（强制）

| # | 场景 | 受影响文档 |
|---|------|------------|
| M1 | 新增 / 删除 / 重构 Python 模块或函数 | SDD + DDS + Interface |
| M2 | 修改核心算法（JMA / ATR / Pivot / StateMachine） | DDS 强制，SDD 架构图需同步 |
| M3 | 新增输出列（DataFrame schema 变更） | DDS 输出列清单 + Interface |
| M4 | 修改 CLI 参数或新增参数 | SDD CLI 章节 + Interface |
| M5 | 新增测试用例或测试策略变更 | Test Cases |
| M6 | 新增 Portfolio 配置或格式变更 | SDD Portfolio 章节 |
| M7 | 修改目录结构或路径约定 | SDD 目录结构章节 |
| M8 | Bug fix 导致算法行为变更 | DDS 算法章节 + Test Cases |
| M9 | 新增/修改依赖包 | SDD 技术栈章节 |
| M10 | 新增指标（通过 IndicatorEngine 接入） | SDD 扩展性 + DDS 新增章节 + Interface + Test Cases |

### 3.2 允许跳过文档更新的场景

| # | 场景 | 说明 |
|---|------|------|
| S1 | 仅修改注释/docstring，无功能变更 | PATCH 可选更新 |
| S2 | 仅修改 `.pyc` 或缓存文件 | 无需更新 |
| S3 | 仅修改测试数据 CSV（不影响代码） | 无需更新 |
| S4 | 仅修改图表样式/颜色（可视化层） | SDD 可选更新 |
| S5 | 修复 CI/CD 配置错误 | 无需更新 |

---

## 4. 变更流程

### 4.1 标准流程（建议）

```
1. 代码变更实施
       ↓
2. 同步修改对应的设计文档
       ↓
3. 在 CHANGELOG.md 新增变更条目
       ↓
4. 更新文档版本号（PATCH / MINOR / MAJOR）
       ↓
5. 提交 Commit（建议带 [DOC] 前缀）
```

### 4.2 Commit 规范

```
[DOC] <type>: <简短描述>

类型 (type):
  arch     - 架构变更（SDD）
  algo     - 算法变更（DDS）
  api      - 接口变更（Interface）
  test     - 测试用例变更（Test Cases）
  fix      - 文档修正
  perf     - 性能/优化说明更新
  docs     - 多份文档同步更新

示例：
  [DOC] algo: JMA 算法由递归改为向量化实现
  [DOC] api:  新增 get_indicator_config() 接口
  [DOC] test: 新增 BreakoutStateMachine 边界用例 3 条
  [DOC] docs: 修正 SDD 目录结构 + 更新 DDS 输出列清单
```

### 4.3 版本升级决策

```
变更后自问：
  1. 是否改变了函数的入参/返回值？       → Interface → MINOR
  2. 是否改变了算法逻辑或公式？           → DDS → MINOR/MAJOR
  3. 是否影响了其他模块的调用关系？       → SDD → MINOR
  4. 是否新增了必须被测试的功能？         → Test Cases → MINOR
  5. 以上全部 → 全部同步升级，评估 MAJOR
```

---

## 5. CHANGELOG 管理规范

### 5.1 格式要求

CHANGELOG.md 位于项目根目录，每次变更在顶部追加新条目：

```markdown
## [1.2.0] — 2026-05-01

### 新增
- SDD: 新增 RSI 指标扩展性章节（IndicatorEngine.register）
- DDS: 新增 RSI 指标算法公式章节
- Interface: 新增 `RSIIndicator` 类定义
- Test Cases: 新增 RSI 相关测试用例 8 条

### 修复
- DDS: 修正 JMA beta 系数说明中的括号优先级错误
- Interface: 修正 `BreakoutStateMachine.update()` 返回值描述

### 变更
- SDD: 更新目录结构，新增 `src/indicators/rsi.py`
- DDS: `atr` 输出列默认值说明更新
```

### 5.2 版本状态定义

| 状态 | 含义 |
|------|------|
| `[x.y.z]` | 已发布正式版本 |
| `[x.y.z-beta]` | 预发布版本（文档草稿中，代码未完成） |
| `[x.y.z-wip]` | 进行中（部分变更已实施，文档待完成） |

---

## 6. 文档模板与格式规范

### 6.1 必需的头部元数据

每份设计文档必须包含以下头部（所有文档头部格式统一）：

```markdown
# A_share 项目 — <文档类型>

> **项目名称**：A_share — A 股技术分析指标系统
> **版本**：<MAJOR.MINOR.PATCH>
> **日期**：<YYYY-MM-DD>
> **文档版本历史**：见 CHANGELOG.md
> **审批人**：SimonLiao

---
```

### 6.2 文档头部字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| 项目名称 | 固定 | A_share — A 股技术分析指标系统 |
| 版本 | 语义化版本号 | 1.2.0 |
| 日期 | 本次版本发布日期 | 2026-05-01 |
| 文档版本历史 | 指向 CHANGELOG | 见 CHANGELOG.md |
| 审批人 | 固定 | SimonLiao |

### 6.3 文档目录结构

```
A_share/
├── docs/                          # 文档资源
│   ├── DOC_VERSIONING.md         # 本规范文件
│   └── template/
│       ├── SDD_template.md       # SDD 模板
│       ├── DDS_template.md       # DDS 模板
│       ├── Interface_template.md # 接口模板
│       └── Test_Cases_template.md # 测试用例模板
├── CHANGELOG.md                  # 变更追踪（根目录）
├── A_share_SDD.md               # 核心文档（根目录）
├── A_share_DDS.md               # 核心文档（根目录）
├── A_share_Interface.md         # 核心文档（根目录）
└── A_share_Test_Cases.md        # 核心文档（根目录）
```

---

## 7. 版本化检查清单

每次代码变更后，用以下清单确认文档是否需要更新：

```
[ ] M1  新增/删除/重构模块  → SDD + DDS + Interface 同步更新？
[ ] M2  核心算法变更        → DDS 算法公式 + SDD 架构图 + Test Cases 同步更新？
[ ] M3  输出列 schema 变更  → DDS 输出列清单 + Interface 同步更新？
[ ] M4  CLI 参数变更       → SDD CLI 章节 + Interface 同步更新？
[ ] M5  测试用例新增/变更   → Test Cases 更新？
[ ] M6  Portfolio 配置变更  → SDD Portfolio 章节更新？
[ ] M7  目录/路径变更       → SDD 目录结构章节更新？
[ ] M8  Bug fix 行为变更    → DDS + Test Cases 同步更新？
[ ] M9  依赖包变更          → SDD 技术栈章节更新？
[ ] M10 新增指标接入        → SDD + DDS + Interface + Test Cases 全部同步更新？

若以上任何一项为"是"：
  [ ] 在 CHANGELOG.md 顶部新增变更条目
  [ ] 评估版本升级级别（PATCH / MINOR / MAJOR）
  [ ] 更新受影响的文档版本号和日期
  [ ] 提交 Commit，带 [DOC] 前缀
```

---

## 8. 相关文件

| 文件 | 用途 |
|------|------|
| `CHANGELOG.md` | 变更历史总表，按版本倒序排列 |
| `docs/template/*.md` | 文档模板，确保新增文档符合格式规范 |
| `.docignore` | 文档目录中不需要版本化的文件（如草稿、备份） |

---

## 9. 维护者规则

- **文档责任人**：项目开发者（所有代码变更者均为文档维护者）
- **文档审批人**：SimonLiao（负责审批所有设计文档变更）
- **文档审查**：PR 合并前，Reviewer 应检查是否满足版本化检查清单；审批人 SimonLiao 对文档内容变更拥有最终批准权
- **版本锁定**：CHANGELOG 一旦添加条目，**禁止删除或修改已发布的版本块**
- **草稿机制**：若有重大变更在进行中，可在 CHANGELOG 顶部添加 `[x.y.z-wip]` 标记，代码合并后改为正式版本号

---

*本文档与 CHANGELOG.md 共同构成 A_share 项目的文档版本管理体系。
任何文档相关的争议，以 DOC_VERSIONING.md 的规则为准。*
