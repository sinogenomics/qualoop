# -*- coding: utf-8 -*-
import os
import sys
import io

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

report_path = r"e:\20260502_MZH\Qualoop\reports\open_source_research.md"

with io.open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

timeline_insert = u"""### 📅 第十四次调研（2026-05-23）: 深入分析 Hugging Face smolagents 的代码智能体执行器、browser-use 的 VLM 网页端自动化交互与 Meta Llama Stack 的标准化智能体网关安全防御

#### 1. Hugging Face smolagents (轻量级代码优先智能体框架)
*   **核心创新一：代码型工具调用与推理引擎 (Code-agentic Tool Use & Reasoning)**
    *   *机制原理*：传统 Agent 调用工具依赖于复杂的 JSON 或 Function Calling。smolagents 采用“代码作为行动（Code-as-action）”的范式。Agent 在做出决策时，直接编写包含循环、变量、数学运算的 Python 代码块来调用工具。这种方式显著提高了 LLM 执行多步骤复杂逻辑时的准确度，减少了多轮冗长 API 交互带来的上下文膨胀与幻觉。
*   **核心创新二：限制性 Python 解释器沙盒 (Restricted Python Interpreter Sandbox)**
    *   *机制原理*：为了安全运行 Agent 生成的任意 Python 代码，smolagents 内置了一个轻量级的安全 Python 解释器（PythonInterpreter）。该解释器通过纯 AST 解析与黑白名单拦截执行，不仅不依赖外部容器，还能严格限制文件系统访问、网络通信、内存及 CPU 耗用。它能在极低延迟下安全阻断恶意越权操作，为本地自动执行注入了安全的微型沙盒保障。

#### 2. browser-use (VLM 驱动的端到端浏览器自动化交互框架)
*   **核心创新一：多模态视觉-语言模型网页导航 (Vision-Language Model GUI Navigation)**
    *   *机制原理*：在自动化的 Tester 进行 E2E 界面验证或动态网站交互时，传统方法极度依赖 CSS Selector。browser-use 通过视觉-语言模型（VLM）和 Playwright 深度结合，在每一动作步捕获页面视口截图，并与精简的 DOM 布局树结合输入模型。这使得 Agent 能像人类一样，通过看图识别按钮、表单和动态组件，大幅提高了在现代复杂单页应用（SPA）中的导航鲁棒性。
*   **核心创新二：动态交互 DOM 节点压缩与动作空间简化 (Dynamic DOM Compression & Minimal Action Space)**
    *   *机制原理*：为了在有限的 LLM 上下文中高效塞入网页 DOM，browser-use 内置了自适应的 DOM 过滤器。它过滤掉无交互的噪声标签（如无事件监听 of div/span），为所有可点击、可输入的交互节点标上全局唯一的数字索引，并将 Agent 的动作空间压缩为极简的指令集（如 `click(index)`, `type(index, text)`, `scroll_down()`），极大节约了上下文 Tokens。

#### 3. Meta Llama Stack (标准化智能体 API 与安全防御护盾网关)
*   **核心创新一：统一的智能体技术栈 API 标准规范 (Unified Agentic Stack API Standard)**
    *   *机制原理*：为了打破各家 Agent 框架与模型强绑定的壁垒，Llama Stack 定义了一套涵盖推理、安全检查（Shields）、记忆检索（Memory）、工具调用（Tools）的标准化 API 网关。通过这一网关，Qualoop 可以与模型提供商、向量数据库、隔离环境解耦，所有的智能体角色都可以通过统一的 JSON-RPC 或 REST API 与底层基础设施通信，实现了生产级的组件可替换性。
*   **核心创新二：双向内置安全护盾网关 (Inline Safety Shields with Llama Guard)**
    *   *机制原理*：防范恶意 Prompt 注入以及 LLM 泄露敏感数据是 L3/L4 级的关键保障。Llama Stack 内置了双向防护网关，将 Llama Guard / Code Shield 模块集成至推理管道中。在 Agent 输入端检查是否有越狱和注入风险，在输出端检查生成的代码是否包含恶意破坏性系统命令或越权凭证泄漏，通过物理隔离的双向防火墙机制，将安全防御推到网关层。

```mermaid
graph TD
    subgraph smolagents-Framework
        LLMCode[Agent Logic Generator] -->|Generates Python Code| ExecEngine[AST Safe Interpreter]
        ExecEngine -->|REST/Local Call| LocalTools[Predefined Local Tools]
        LocalTools -->|Execution Output| ExecEngine
        ExecEngine -->|Variables & Returns| LLMCode
    end
    subgraph browser-use-Web
        Playwright[Playwright Browser Browser] -->|Capture Screenshot & DOM| CompNode[DOM Compressor]
        CompNode -->|Numbered Interactive Elements| VLM[Vision LLM Planner]
        VLM -->|Action: click/type/scroll| Playwright
    end
    subgraph LlamaStack-Gateway
        UserAgent[Qualoop Agent Core] -->|Unified API Request| APIReq[Llama Stack API Gateway]
        APIReq -->|1. Input Check| InputShield[Llama Guard Input Shield]
        InputShield -->|Safe| ModelInference[LLM Agent Inference]
        ModelInference -->|Generate Actions| OutputShield[Code Guard Output Shield]
        OutputShield -->|Intercept Safe Command| UserAgent
    end
```"""

target_split = u"""        Context[Context docs / logs] & Answer[Agent Output / Report] -->|Split into assertions| Faith[Faithfulness Evaluator]
        Faith -->|Check Entailment| ScoreF[Faithfulness Score]
        Answer -->|Reverse questions| Rel[Answer Relevancy Evaluator]
        Rel -->|Embedding Similarity| ScoreR[Answer Relevancy Score]
    end
```"""

if target_split not in content:
    target_split = target_split.replace(u'\n', u'\r\n')

if target_split not in content:
    print("Error: target split not found!")
    sys.exit(1)

parts = content.split(target_split)
content = parts[0] + target_split + u"\n\n---\n\n" + timeline_insert + u"\n" + target_split.join(parts[1:])

# Table replacements
old_sec_safety = u"""| **执行安全性** | 本地终端直接运行，无沙盒 | **SWE-agent**: Docker 沙盒隔离 (SWE-ReX)<br>**Aider**: Git 自动 Commit/Rollback<br>**GPT-Pilot**: SQLite 状态保存与回滚<br>**AutoGen**: 原生 Docker 执行器<br>**OpenHands**: Docker Sandbox Runtime & 持续 Tmux 会话<br>**E2B Sandboxes**: Firecracker MicroVM 物理硬件级 KVM 隔离<br>**SWE-bench**: Docker 细粒度版本复现与 Git Patch 验证 | **极高**：结合微虚拟机隔离（如 E2B）、Git 微步回滚与 SWE-bench 风格的 Docker 依赖版本锚定与 Git Patch 自动校验，建立极致安全的执行与验证沙盒。 |"""
new_sec_safety = u"""| **执行安全性** | 本地终端直接运行，无沙盒 | **SWE-agent**: Docker 沙盒隔离 (SWE-ReX)<br>**Aider**: Git 自动 Commit/Rollback<br>**GPT-Pilot**: SQLite 状态保存与回滚<br>**AutoGen**: 原生 Docker 执行器<br>**OpenHands**: Docker Sandbox Runtime & 持续 Tmux 会话<br>**E2B Sandboxes**: Firecracker MicroVM 物理硬件级 KVM 隔离<br>**SWE-bench**: Docker 细粒度版本复现与 Git Patch 验证<br>**smolagents**: AST 级别限制性本地 Python 解释器沙盒 | **极高**：结合微虚拟机隔离（如 E2B）、Git 微步回滚、SWE-bench 风格的 Docker 依赖版本锚定与 Git Patch 校验，并引入 smolagents 风格的本地 AST 限制性 Python 沙盒，实现多层次安全防护。 |"""
content = content.replace(old_sec_safety, new_sec_safety)

old_sec_cmd = u"""| **命令/交互形式** | 自然语言转 Python 脚本或 CLI | **SWE-agent**: 裁剪的高密 ACI 指令集<br>**GPT-Pilot**: 交互式微任务人工确认<br>**LangGraph**: 状态机中断与时间旅行<br>**Agent Protocol**: 通用 RESTful 任务/步骤标准协议<br>**Dify**: 可视化工作流引擎与 GUI-API 同步机制<br>**Vercel AI SDK**: 跨提供商统一流式生成与 Client-UI 同步 | **高**：设计 `qualoop-shell`，对接 Agent Protocol RESTful 标准，并可集成 Dify 的可视化工作流调试，支持基于 Vercel AI SDK 的边缘流式状态同步。 |"""
new_sec_cmd = u"""| **命令/交互形式** | 自然语言转 Python 脚本或 CLI | **SWE-agent**: 裁剪的高密 ACI 指令集<br>**GPT-Pilot**: 交互式微任务人工确认<br>**LangGraph**: 状态机中断与时间旅行<br>**Agent Protocol**: 通用 RESTful 任务/步骤标准协议<br>**Dify**: 可视化工作流引擎与 GUI-API 同步机制<br>**Vercel AI SDK**: 跨提供商统一流式生成与 Client-UI 同步<br>**browser-use**: VLM 驱动的 GUI 网页导航与 DOM 节点压缩交互 | **高**：设计 `qualoop-shell`，对接 Agent Protocol RESTful 标准，集成 Dify 工作流与 Vercel AI SDK，并参考 browser-use 引入 VLM 驱动的 GUI 网页导航，大幅拓宽 Tester 的自动化交互空间。 |"""
content = content.replace(old_sec_cmd, new_sec_cmd)

old_sec_def = u"""| **防退化与安全防御** | 无静态安全检查，完全信任 LLM 生成 | **OpenHands**: 拦截式 Security Analyzer 安全审查 | **高**：在命令执行器层增加拦截式安全检测插件，识别并拦截破坏性命令。 |"""
new_sec_def = u"""| **防退化与安全防御** | 无静态安全检查，完全信任 LLM 生成 | **OpenHands**: 拦截式 Security Analyzer 安全审查<br>**Llama Stack**: 推理与工具调用双向 Llama Guard 安全护盾 | **高**：在命令执行层增加拦截式安全扫描器，并参考 Llama Stack 引入双向 Llama Guard 输入输出过滤与敏感数据拦截防火墙。 |"""
content = content.replace(old_sec_def, new_sec_def)

# Suggestion additions
old_sugg39 = u"""    > **升级建议三十九（基于 Docker 的细粒度运行时版本依赖锚定与 Git Patch 自动校验）**：参考 SWE-bench，为 L3/L4 的自动修复和验证流水线引入细粒度版本复现镜像。为每个需要修复的 Issue/模块构建独立的 Docker 沙盒，锁定 Python 及第三方库版本。Executor 执行完后仅提取 Git Patch (diff) 并应用到干净的环境中，通过 FAIL_TO_PASS 和 PASS_TO_PASS 双重回归测试套件校验修复的正确性，杜绝依赖漂移和副作用。"""
new_sugg39 = old_sugg39 + u"""
    >
    > **升级建议四十五（基于 smolagents Code-first 的代码型工具调用与限制性 AST 沙盒）**：参考 smolagents，在 Executor 模块引入代码优先的工具交互模式。当 Executor 需要执行多步骤复杂操作（如批量修改文件并同时执行本地统计）时，允许其编写包含循环控制和局部变量的 Python 代码段，并通过内置的 AST 安全解释器执行，在不启动笨重 Docker 的前提下限制系统越权操作，提高逻辑执行效率。"""
content = content.replace(old_sugg39, new_sugg39)

old_sugg37 = u"""    > **升级建议三十七（基于 Vercel AI SDK 的多提供商统一流抽象与状态同步）**：参考 Vercel AI SDK，重构 Qualoop 底层的 `llm_client.py`。设计统一的模型提供商代理接口，无缝切换 OpenAI、Anthropic、Gemini 或本地 Ollama 模型；并引入边缘级 Token 流式响应（streamText）与客户端实时 UI 状态同步，使复杂的 Executor 代码生成和 Scorer 打分过程能够实时同步至外部监控页面，提供秒级的进度反馈。"""
new_sugg37 = old_sugg37 + u"""
    >
    > **升级建议四十六（基于 browser-use 的多模态 VLM 浏览器交互与动态 Tester 页面评测）**：参考 browser-use，升级 Tester 对 Web 项目的可观测性与自动化测试范围。通过 Playwright 驱动浏览器，并在每一步合并 VLM 页面截图与压缩过滤后的交互式 DOM 树。使 Tester 能够通过多模态视觉智能体直接与动态 Web 界面交互，点击元素、键入文本并截图对比，开展强鲁棒性的端到端 UI 测试验证。"""
content = content.replace(old_sugg37, new_sugg37)

old_sugg44 = u"""    > **升级建议四十四（基于 Promptflow 的可视化多智能体 DAG 链路设计与离线批测试）**：参考 Microsoft Promptflow，在 Qualoop 引入 DAG 流向依赖声明。将各个探针、审查器以节点形式可视化组装，并提供强大的本地批处理测试命令行工具。通过配置离线数据集，自动化对不同的 Agent 组合在特定测试场景下的平均 MTTR 和修复率进行回归分析，提升流水线的交付置信度。"""
new_sugg44 = old_sugg44 + u"""
    >
    > **升级建议四十七（基于 Llama Stack API 标准规范与双向 Llama Guard 防火墙）**：参考 Llama Stack，为 Qualoop 的 Agent 服务引入标准 API 网关，将底层的大模型推理、向量检索（Memory）以及工具执行接口（Tools）完全抽象化。同时，在 Orchestrator 核心调度回路中引入双向内置安全护盾（Shields），在输入端阻断 Prompt 恶意注入与越狱，在输出端实时检测并拦截敏感信息泄露和高危命令。"""
content = content.replace(old_sugg44, new_sugg44)

with io.open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Report updated successfully with Round 14 findings.")
