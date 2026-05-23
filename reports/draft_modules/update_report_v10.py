# -*- coding: utf-8 -*-
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

report_path = r"e:\20260502_MZH\Qualoop\reports\open_source_research.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

timeline_insert = """### 📅 第十次调研（2026-05-23）: 深入分析 Letta (MemGPT) 的操作系统级分层内存与自主心跳机制、TaskWeaver 的代码首要规划与内核沙盒执行、Phidata 的面向对象 Assistant 会话持久化与知识库集成

#### 1. Letta (前 MemGPT - 面向操作系统架构的智能体内存管理框架)
*   **核心创新一：OS-style Hierarchical Memory Architecture (操作系统级分层内存管理)**
    *   *机制原理*：传统智能体将全部历史聊天直接喂给大模型上下文窗口，容易在超长会话中超出 Limit 或因噪声丢失关键记忆。Letta 参照 OS 对 RAM 和 Disk 的管理方式，将智能体内存划分为三层：
        1.  `Core Memory` (类似于 RAM)：包括 `user_context` (用户画像)、`agent_context` (智能体自画像) 和 `scratchpad` (临时工作区)。它是直接且实时存在于 LLM 提示词上下文中的，智能体可以使用专门的工具（如 `core_memory_append`）在运行时主动读取或改写该区域。
        2.  `Recall Memory` (类似于 L2 缓存/归档数据库)：包含智能体过往全部交互历史 Event。智能体通过时间检索、关键字搜索等工具动态召回历史记录。
        3.  `Archival Memory` (类似于 Hard Disk 外部数据库)：用于存储非结构化海量文档资料。智能体通过 Vector Embedding 检索动态将片段加载到上下文。
*   **核心创新二：Self-directed Heartbeat Loop & Non-blocking Step Execution (自主心跳驱动非阻塞执行)**
    *   *机制原理*：传统智能体是事件响应式的（用户发一条，智能体回一条）。Letta 引入了 Heartbeat 机制，允许智能体在发出指令的同时显式触发“步进（Step）”信号。如果在当前 step 中没有人类介入，系统会产生一个虚构的 System Message（如 `heartbeat_reason`）重新调起模型。通过连续的心跳循环，Letta 智能体可以自主决定是否需要调用 Recall 检索、编辑 Core Memory，并再次发起外部 Tool Call，直至任务完全终止。

#### 2. TaskWeaver (微软开源的 Code-First 数据分析与规划智能体框架)
*   **核心创新一：Code-First Planning with Schema-backed Tool Binding (代码首要规划与模式支持的工具绑定)**
    *   *机制原理*：传统智能体使用 Function Calling 时，大模型只能以 JSON 参数调用静态定义的 Tool API。在处理复杂的多步骤计算、临时算法处理以及结构化数据流（如 Pandas Dataframe 传递）时极易出错。TaskWeaver 采用“代码首要”的设计：Orchestrator 将用户的高级目标规划并翻译成临时的、动态编写的 Python 代码，而在 Python 代码中，则通过导入 Schema 文件描述的 Tool 插件类进行强类型调用。这种方式允许智能体在代码中声明复杂的局部循环、自定义数学变换，极大增强了任务表征的自由度。
*   **核心创新二：Separation of Planner & Code Executor Roles (规划器与沙盒内核执行器角色的严格隔离)**
    *   *机制原理*：TaskWeaver 将系统拆分为 `Planner` 和 `Code Generator (CG)` / `Code Executor (CE)` 两大角色。Planner 直接与用户对接，梳理逻辑链与里程碑并将其下发给 CG；CG 专职编写 Python 脚本；CE 则在后台运行一个独立的、带有进程和变量状态保持的 Jupyter 交互式内核环境。CE 执行生成的 Python 代码并将执行的 stdout/stderr、错误栈以及新生成的临时图表返回给 CG 进行自愈验证。两个角色的运行上下文完全物理隔离，防止了不受信代码侵入核心控制流。

#### 3. Phidata (面向对象的智能体应用与多层持久化存储框架)
*   **核心创新一：Object-Oriented Assistant State & Session Persistence (面向对象 Assistant 状态与多数据库 Session 持久化)**
    *   *机制原理*：很多智能体框架的状态散落在各个全局变量和文件系统中，不利于做多租户并发、运行中断恢复和多端同步。Phidata 采用高度封装的面向对象设计，将智能体的所有运行时状态（包括 Chat History、Model Parameters、Tool Calls、System Prompt、Session ID）完全囊括在一个 `Assistant` 实例中。通过实现底层的 SQL 数据库存储适配器（如 `PgAssistantStorage`、`SqliteAssistantStorage`），只需一行配置即可将整个 Agent 的实时状态无缝持久化至关系型数据库。
*   **核心创新二：Semantic Search Tool Routing & Native Structured Outputs (语义搜索工具路由与原生强类型输出控制)**
    *   *机制原理*：Phidata 原生内置了将知识库（Knowledge Base）与向量数据库（PgVector, LanceDB）无缝绑定到 Agent 的设计。在 LLM 接收到请求前，框架自动进行向量语义检索，并将最相关的 Context 以增强上下文注入 Prompt 中。同时，Phidata 提供了对 Pydantic 的原生适配，支持在 Assistant 级别强制限制模型返回特定的 Pydantic Model 结构。即使底层 LLM 不支持结构化输出 API，Phidata 也会通过后置 Parser 以及自动 Validation Retry 机制保障输出绝对可解析。

```mermaid
graph TD
    subgraph Letta-OS-Memory
        LLMContext[LLM Context Window] <-->|1. Live core read/write| Core[Core Memory: user/agent profile & scratchpad]
        LLMContext -->|2. Search & Page-in| RecallDB[(Recall Db: Events)]
        LLMContext -->|3. Embedding Query| ArchivalDB[(Archival Db: Vector Search)]
        LLMRunner[Letta Runner] -->|Heartbeat Event| LLMContext
    end
    subgraph TaskWeaver-CodeFirst
        Planner[Planner] -->|High-level Subtask| CG[Code Generator]
        CG -->|Generated Python Code| CE[Code Executor Sandbox]
        CE -->|Execution Output & Variables| CG
    end
    subgraph Phidata-Object-State
        PhidataAgent[Phidata Assistant Object] <-->|Serialize / Deserialize| SQLStore[(SQL Store: Postgres/Sqlite)]
        PhidataAgent -->|Semantic Search| VectorDB[(Vector DB: LanceDB/PgVector)]
        PhidataAgent -->|Pydantic schema validation| Parser[Structured Output Parser]
    end
```"""

target_split = """    subgraph Agent-Protocol-Spec
        Client[External Client / Benchmark Platform] -->|POST /tasks| API[Agent Protocol Server]
        API -->|POST /tasks/{id}/steps| AgentCore[Qualoop Agent Core]
        AgentCore -->|Update trace & artifacts| DB[(Standardized Step DB)]
    end
```"""

if target_split not in content:
    target_split = target_split.replace('\n', '\r\n')

if target_split not in content:
    print("Error: target split not found!")
    sys.exit(1)

parts = content.split(target_split)
content = parts[0] + target_split + "\n\n---\n\n" + timeline_insert + "\n" + target_split.join(parts[1:])

# Table Row replacements
old_context = """| **上下文管理** | 静态读取特定文件与 issues 列表 | **Aider**: Tree-sitter PageRank 代码地图<br>**Devin**: 动态 Memory + 本地规则库<br>**CrewAI**: 三层记忆机制 (短期/长期/实体) | **极高**：结合 PageRank 代码地图与 CrewAI 风格 of 向量库长期记忆，避免长周期运行中上下文失效。 |"""
new_context = """| **上下文管理** | 静态读取特定文件与 issues 列表 | **Aider**: Tree-sitter PageRank 代码地图<br>**Devin**: 动态 Memory + 本地规则库<br>**CrewAI**: 三层记忆机制 (短期/长期/实体)<br>**Letta**: 操作系统级分层内存 (Core/Recall/Archival)<br>**Phidata**: 基于数据库 (PostgreSQL/SQLite) 的 Session 持久化 | **极高**：结合代码地图、Letta 风格的分层内存管理以及 Phidata 的 Session 状态持久化，解决超长周期运行下的上下文过载与信息丢失。 |"""
content = content.replace(old_context, new_context)

old_self_heal = """| **自愈与控制链** | 一次性执行修复，失败则退出 | **Devin**: ReAct 自主规划与 3 次重规划循环<br>**GPT-Pilot**: 编译/测试失败自动触发 Debug 流 | **极高**：为 Executor 引入有界自纠错循环状态机，当 Verifier 失败时自动重规划。 |"""
new_self_heal = """| **自愈与控制链** | 一次性执行修复，失败则退出 | **Devin**: ReAct 自主规划与 3 次重规划循环<br>**GPT-Pilot**: 编译/测试失败自动触发 Debug 流<br>**Letta**: 自主心跳 (Heartbeat) 非阻塞循环机制 | **极极高**：为 Executor 引入有界自纠错状态机，并参考 Letta 引入自主心跳驱动的非阻塞循环，实现完全自主的任务推动。 |"""
content = content.replace(old_self_heal, new_self_heal)

old_plugin = """| **插件化与治理** | 硬编码在 scripts 目录，依赖特定接口 | **Semantic Kernel**: 标准化插件目录与依赖注入<br>**Pydantic AI**: 基于 Pydantic 强类型约束 of Tool 依赖注入<br>**Agency**: 基于 Actor 权限模型与 ACL 的工具治理 | **高**：探针与动作插件化，结合 Pydantic AI 的依赖注入，引入 Agency 风格的 Actor ACL 权限拦截器，实现细粒度安全访问。 |"""
new_plugin = """| **插件化与治理** | 硬编码在 scripts 目录，依赖特定接口 | **Semantic Kernel**: 标准化插件目录与依赖注入<br>**Pydantic AI**: 基于 Pydantic 强类型约束 of Tool 依赖注入<br>**Agency**: 基于 Actor 权限模型与 ACL 的工具治理<br>**TaskWeaver**: 代码首要 (Code-First) 规划与动态 Tool 绑定 | **高**：探针与动作插件化，结合 Pydantic AI 的依赖注入和 Agency 权限拦截器，参考 TaskWeaver 引入动态 Python 代码生成与沙盒执行以增强 Tool 扩展性。 |"""
content = content.replace(old_plugin, new_plugin)


# Suggestion replacements
old_sugg3 = """    > **升级建议三（语法分析地图）**：引入 Python `tree-sitter` 绑定，对整个业务库生成符号依赖表（`automation/repo_map.json`）。当 Tester 探测到某个函数异常时，顺着依赖链把所有的可能调用方（Caller）标注为潜在缺陷 Issue 并写入 Store，实现深度可追溯。"""
new_sugg3 = old_sugg3 + """
    >
    > **升级建议三十三（基于 Letta 与 Phidata 的分层上下文及 Session 记忆管理）**：参考 Letta，为 Tester 与 Executor 引入分层内存控制。将运行时上下文划分为 Core Memory（用于保存 North Star 约束、当前任务子目标和自画像，允许 LLM 在运行中通过工具直接读写）、Recall Memory（历史开发与修复的事件流水）和 Archival Memory（外部向量知识库）。结合 Phidata 适配器，将完整的运行时 Session（包含内存与 Tool 状态）直接持久化存储至 SQLite/Postgres，支持超长周期开发流的随时挂起与精确恢复。"""
content = content.replace(old_sugg3, new_sugg3)

old_sugg6 = """    > **升级建议六（自纠错与重规划状态机）**：为 Executor 引入有界自纠错循环状态机。当 Verifier 反馈编译报错或单测失败时，捕获异常堆栈和错误日志，再次唤起修复 Agent 进行 `Re-planning`。最大自愈尝试限制设为 3 次，超过则置信度归零并自动降级为 `requires_human: true`。"""
new_sugg6 = old_sugg6 + """
    >
    > **升级建议三十四（基于 TaskWeaver 的代码首要规划与执行内核隔离）**：参考 TaskWeaver，改变 Executor 只能生成补丁或运行静态命令的局限。允许 Executor 动态生成用于诊断、执行或验证的临时 Python 脚本，并在后台挂载的 Jupyter-like 交互式内核沙盒（CE）中独立运行。CE 将 stdout/stderr 及新生成的变量数据反馈给规划器。由于执行器与规划器的环境完全隔离，能够在执行复杂修复与本地分析时提供极强的业务表达自由度与安全性。"""
content = content.replace(old_sugg6, new_sugg6)

old_sugg15 = """    > **升级建议十五（Critic-Programmer 自适应会话纠错）**：参考 AutoGen，在 L3 级别的 Executor 执行单元测试修复遇到瓶颈（例如连续两次自纠错失败）时，自适应组建一个临时“诊断聊天组”（Programmer-Critic-Tester）。让 Programmer（写 Diff 的 Executor）、Critic（Scorer）与 Tester 在统一的对话上下文中进行动态发言轮候。由 Tester 运行测试反馈控制台 Traceback，Scorer 实时评估并提出具体修改策略，引导 Programmer 精准调整，直至测试成功或耗尽 Token 额度。"""
new_sugg15 = old_sugg15 + """
    >
    > **升级建议三十五（基于 Letta 的自主心跳驱动非阻塞循环）**：参考 Letta，改变 Qualoop 依赖单向命令行触发的响应式设计。允许 Executor 与 Orchestrator 在执行长任务（如重构整个组件）时，在输出响应中请求 `heartbeat: true`。调度系统据此发出心跳信号，以非阻塞的方式持续调度该 Agent 执行下一步思考或 Tool 调用，直至其主动输出 `is_last_step: true` 或超出最大心跳周期。"""
content = content.replace(old_sugg15, new_sugg15)


with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Report updated successfully with Round 10 findings.")
