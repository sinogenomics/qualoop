# -*- coding: utf-8 -*-
import os
import sys

# Force stdout/stderr to use utf-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

report_path = r"e:\20260502_MZH\Qualoop\reports\open_source_research.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

timeline_insert = """### 📅 第八次调研（2026-05-23）: 深入分析 OpenAI Swarm 的轻量级 Handoff 路由移交、Pydantic AI 的类型安全结构化运行时与依赖注入、AgentOps 的全生命周期飞行记录仪审计与监控

#### 1. OpenAI Swarm (轻量级多智能体协同编排模式)
*   **核心创新一：基于 Agent & Tool Handoff（移交控制权）的轻量级路由**
    *   *机制原理*：传统多智能体框架使用中心化的 Orchestrator 控制流程流转，配置繁琐且容易在长周期会话中产生死锁。Swarm 提出极其精简的路由哲学：**智能体可以通过在 Tool 中返回另一个智能体实例来直接将控制权移交（Handoff）**。每一个 Agent 都包含一组 Tool（函数），其中某些 Tool 可以被定义为路由函数（例如 `transfer_to_scorer()` 返回 `ScorerAgent`）。当 LLM 在 Tool Calling 中决策调用该路由函数时，Swarm 的轻量级 Runner 会拦截该响应，并自动将后续会话上下文切换到目标 Agent 实例中。
*   **核心创新二：极简的无状态对话循环（Stateless Chat Loop）**
    *   *机制原理*：Swarm 的核心运行器 `client.run()` 本身是完全无状态的。它接收当前活跃 Agent、消息列表以及上下文变量，执行多轮 Tool 调用（包含 LLM 交互）直到没有 Handoff 或普通 Tool 待执行，然后将最新的 Message 列表和最终的 Active Agent 返回给外部。整个流转逻辑完全内嵌在 Agent 的 Tool 返回中，天然支持动态分支和多路自适应移交。

#### 2. Pydantic AI (类型安全的结构化 Agent 编程框架)
*   **核心创新一：原生 Pydantic 运行时类型校验与结构化输入输出**
    *   *机制原理*：传统 Agent 在接收和返回 JSON 数据时十分脆弱，模型经常返回缺少关键字段的损坏数据，导致解析崩溃。Pydantic AI 利用 Pydantic v2 的极致性能，为 Agent 的 `deps_type`、`result_type` 等设定强类型约束。LLM 的每一次工具调用和结果返回在运行时均经过严格 Pydantic 校验。如果校验失败，框架会自动捕获错误并将详细的类型不合规信息反馈给 LLM，促使其自动纠错，以工程化手段确保数据边界的安全。
*   **核心创新二：类型安全的依赖注入（Type-Safe Dependency Injection）**
    *   *机制原理*：在长周期的 Agent 运行中，需要安全传递各种运行时环境（如数据库连接、只读客户端配置等）。Pydantic AI 提供类型安全的依赖注入系统，通过 `deps` 参数注入环境上下文。所有的 Tool（System Tools / Custom Tools）均被声明为接收特定类型 `RunContext[Deps]` 的函数，从而在多路并发运行和单元测试中消除了全局变量共享的污染隐患。

#### 3. AgentOps (面向 Agent 运行周期的性能跟踪与审计监控平台)
*   **核心创新一：全生命周期事件飞行记录仪（Agent Event Flight Recorder）**
    *   *机制原理*：AgentOps 提供类似黑匣子的追踪 SDK。它可以自动捕获 Agent 会话中的每一次 LLM 调用、Tool 运行、Action 执行以及 Error 发生，并统一序列化为包含父子层级关系（Parent-Child Spans）的事件树。与传统 Log 不同，AgentOps 实时监测 API 费率消耗、LLM 调用延迟以及内存/CPU 抖动，为开发者在后台面板重现、追踪 Agent 的异常决策轨迹提供数据支撑。
*   **核心创新二：会话重放与多维评测指标大盘**
    *   *机制原理*：平台支持 Session Replay（会话回放），允许开发者逐个 Token 地重放 LLM 与 Sandboxes 的交互。结合自主监控的异常指标（例如检测到死循环调用同一 Tool 时触发的 `Infinite Tool Loop Warning`），直接生成 MTTR、运行耗费成本和 LLM 质量评分，是自动化大 backlog 治理的监控基石。

```mermaid
graph TD
    subgraph OpenAI-Swarm-Handoff
        Runner[Swarm Runner Loop] -->|1. Call Tool| TesterAgent[Tester Agent]
        TesterAgent -->|2. Returns ScorerAgent instance| Runner
        Runner -->|3. Handoff Control| ScorerAgent[Scorer Agent]
    end
    subgraph Pydantic-AI-Safety
        LLM[LLM Output] -->|Raw JSON| Validator[Pydantic Validator]
        Validator -->|Validation OK| Success[Structured Output Result]
        Validator -->|Validation Failed| ErrorFeedback[Type Check Error Detail]
        ErrorFeedback -->|Auto Correct Loop| LLM
    end
    subgraph AgentOps-Monitoring
        QualoopApp[Qualoop Core] -->|SDK Agent Events| AgentOpsCloud[AgentOps Server]
        AgentOpsCloud -->|Telemetry & Cost metrics| Dashboard[Session Replay & Budget Warning]
    end
```"""

# Find the end of ChatDev diagram (end of round 7)
target_split = """        Instructor[Instructor Agent] -->|1. Fuzzy Target| Assistant[Assistant Agent]
        Assistant -->|2. Active Clarification Question| Instructor
        Instructor -->|3. Precise Context / Spec| Assistant
        Assistant -->|4. Perfect Code without Hallucination| Output[Clean Code Output]
    end
```"""

if target_split not in content:
    target_split = target_split.replace('\n', '\r\n')

if target_split not in content:
    print("Error: target split not found!")
    sys.exit(1)

parts = content.split(target_split)
content = parts[0] + target_split + "\n\n---\n\n" + timeline_insert + "\n" + target_split.join(parts[1:])

# Replace comparisons in table using triple quotes for safety
old_arch = """| **智能体架构** | 五角色顺序流（发现→评分→分派→执行） | **MetaGPT**: 基于 SOP 的发布-订阅事件总线<br>**CrewAI**: 经理人自适应任务委派机制<br>**AutoGen**: 动态发言人自适应群聊会话<br>**LlamaIndex**: @step 事件驱动路由与 Context 状态<br>**ChatDev**: ChatChain 瀑布流模拟协作与主动反幻觉机制 | **极高**：引入事件总线解耦角色，并支持大任务的 ChatChain 式双智能体协作和澄清机制，防止逻辑失控。 |"""
new_arch = """| **智能体架构** | 五角色顺序流（发现→评分→分派→执行） | **MetaGPT**: 基于 SOP 的发布-订阅事件总线<br>**CrewAI**: 经理人自适应任务委派机制<br>**AutoGen**: 动态发言人自适应群聊会话<br>**LlamaIndex**: @step 事件驱动路由与 Context 状态<br>**ChatDev**: ChatChain 瀑布流模拟协作与主动反幻觉机制<br>**OpenAI Swarm**: 基于 Agent & Tool Handoff 的无状态路由 | **极高**：引入事件总线解耦角色，并支持通过 Handoff 机制实现轻量级控制移交与多路自适应路由。 |"""
content = content.replace(old_arch, new_arch)

old_obs = """| **可观测与可审计** | 静态生成 markdown 报告与 json 状态 | **OpenHands**: Append-Only Event Stream 日志<br>**Langfuse**: 基于 OpenTelemetry 的分层 Traces 追踪与 Prompt 注册表关联 | **极极高**：通过 OpenTelemetry 追踪和 Langfuse 仪表盘展示，将 LLM API 耗时、Token 消耗及 Prompt 版本进行可视化治理与重放审计。 |"""
new_obs = """| **可观测与可审计** | 静态生成 markdown 报告与 json 状态 | **OpenHands**: Append-Only Event Stream 日志<br>**Langfuse**: 基于 OpenTelemetry 的分层 Traces 追踪与 Prompt 注册表关联<br>**AgentOps**: 包含会话回放与费率追踪的飞行记录仪监控 | **极极高**：通过 OTel 及 AgentOps 遥测，实现全生命周期会话回放、API 耗时/资费追踪以及死循环警告检测。 |"""
content = content.replace(old_obs, new_obs)

old_plugin = """| **插件化与治理** | 硬编码在 scripts 目录，依赖特定接口 | **Semantic Kernel**: 标准化插件目录与依赖注入 | **中高**：将发现探针（Tester）、修复动作（Executor）插件化，通过依赖注入管理各角色关联的 LLM 实例与配置。 |"""
new_plugin = """| **插件化与治理** | 硬编码在 scripts 目录，依赖特定接口 | **Semantic Kernel**: 标准化插件目录与依赖注入<br>**Pydantic AI**: 基于 Pydantic 强类型约束 of Tool 依赖注入 | **高**：将探针与动作插件化，引入 Pydantic AI 的 `RunContext` 类型安全依赖注入，保障多线程与单元测试的运行隔离。 |"""
content = content.replace(old_plugin, new_plugin)

# Update Suggestion Categories

# Category 9
old_sugg9 = """> **升级建议二十四（基于 ChatChain 的多角色交互式编码）**：在 Executor 内部细分出 Programmer 和 Reviewer 角色，设计专用的 ChatChain 交互规则。两者不通过单一 Prompt 串行运行，而是以瀑布流 SOP 在局部开展多轮深入对话，Programmer 负责写 Diff，Reviewer 负责走 AST 校验与 Review 驳回，直到达成共识再把代码抛给 Verifier 校验，以角色对抗和博弈抑制幻觉。"""
new_sugg9 = old_sugg9 + """
    >
    > **升级建议二十六（基于 Handoff 的自适应轻量级协作）**：参考 OpenAI Swarm，在各角色协同中引入轻量级的 Handoff 机制。当 Tester 检测到特定类型 Issue 时，可通过直接调用 Tool 并返回指定的 Scorer 实例来转移控制权，消除中心化调度器的开销，支持更敏捷的角色流转。"""
content = content.replace(old_sugg9, new_sugg9)

# Category 10
old_sugg10 = """> **升级建议十二（G-Eval 多维 Logprobs 加权评分）**：参考 DeepEval，升级 Scorer 的 LLM 评分器。不再要求 LLM 直接返回一个数值，而是先生成详细的评估步骤（Evaluation Steps），接着在打分时提取打分 token 的 Logprobs，通过概率加权计算得分，规避大模型打分的极端值和主观偏移，实现高确定性的价值打分闭环。"""
new_sugg10 = old_sugg10 + """
    >
    > **升级建议二十七（Pydantic 运行时类型校验与自愈）**：参考 Pydantic AI，在 Scorer 定性打分和 Executor 生成代码阶段使用 Pydantic v2 进行强类型 Schema 校验。一旦解析 JSON 或补丁失败，自动捕获 validation 详细异常回喂给 LLM 触发自我修正循环，确保系统数据流绝对安全。"""
content = content.replace(old_sugg10, new_sugg10)

# Category 12
old_sugg12 = """> **升级建议二十三（版本化 Prompt 注册表管理）**：集成 Langfuse Prompt Registry，不再将提示词（如 Scorer 评价指标、Executor 角色设定）硬编码于 python 源码中，而是通过 Langfuse API 在运行时拉取对应的生产标记（Label = "production"）版本。允许开发者通过 Langfuse 控制台在线灰度与热更新 Prompt。"""
new_sugg12 = old_sugg12 + """
    >
    > **升级建议二十八（类型安全依赖注入）**：参考 Pydantic AI 的 `RunContext[Deps]` 机制，对 Qualoop 的插件依赖和运行时配置进行类型安全的依赖注入，杜绝全局状态共享引起的并发冲突与测试污染。
    >
    > **升级建议二十九（AgentOps 飞行记录仪与死循环监控）**：集成 AgentOps 追踪 SDK。对 Qualoop 进行 Session-level 审计追踪，实时记录 LLM tokens 消耗折算资费，并在检测到多智能体 Tool 调用死循环时触发警报，提升可观测性。"""
content = content.replace(old_sugg12, new_sugg12)

with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Report updated successfully with Round 8 findings.")
