# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 24 Updater
Appends the 24th round of deep research findings to reports/open_source_research.md
and syncs the presentation layer in reports/open_source_research_report.html.
"""
import io
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

workspace = r"e:\20260502_MZH\Qualoop"
report_md_path = os.path.join(workspace, "reports", "open_source_research.md")
report_html_path = os.path.join(workspace, "reports", "open_source_research_report.html")

# Read Markdown
with io.open(report_md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

timeline_insert = u"""### 📅 第二十四次调研（2026-05-23）: 深入分析 LangGraph 的双环验证与状态图中断回滚、AutoGen v0.4 的分布式 gRPC 远程智能体通信与 smolagents 的多智能体工具委派与动态分派

#### 1. LangGraph (双环验证与状态图中断回滚)
*   **核心创新一：双向人机协同与状态中断编辑 (Double-Loop Human-in-the-Loop & State Editing)**
    *   *机制原理*：在自动修复代码时，若遇到置信度低或复杂的问题，直接由 Agent 提交可能导致代码库损坏。LangGraph 提供了图级状态的中断机制（`interrupt_before` 和 `interrupt_after`）。当流程运行到需要人工审查/高风险的节点前时，状态机会自动将状态快照保存并挂起。人类审核者不仅可以批准或驳回，还能在挂起期间直接修改图的状态变量（如注入修改过的 SQL 语句或补齐必要的上下文参数），随后使图恢复执行，实现无缝的人机双环协同。
*   **核心创新二：状态快照时间旅行与任意节点回滚 (State Graph Time-Travel & Node Rollback)**
    *   *机制原理*：多智能体在长时间探索中可能进入死胡同或发生错误决策。LangGraph 能够为每一次状态变更保留完整的快照树。如果之后的步骤运行失败，或者评估器发现分支方向错误，系统可以读取历史快照并进行“时间旅行”，强制将当前的图状态回滚到之前的任意一个节点，丢弃无效的分支尝试，从正确的历史分叉口重新探索。

#### 2. Microsoft AutoGen v0.4 (分布式 gRPC 远程智能体通信)
*   **核心创新一：跨容器/主机分布式智能体集群 (Distributed Agent Runtime over gRPC)**
    *   *机制原理*：在大规模缺陷定位与修复中，如果所有智能体都跑在宿主机或单一进程中，会面临极大的资源争抢和环境污染。AutoGen v0.4 的 Actor 运行时支持通过 gRPC 协议进行低延迟的远程通信。每个 Agent 可以运行在独立隔离的物理容器、甚至不同的服务器上，仅通过定义的 Protobuf 协议进行远程异步消息传递，从而支持物理隔离的多节点并行修复。
*   **核心创新二：动态服务发现与网关路由 (Dynamic Service Discovery & Agent Gateway)**
    *   *机制原理*：当 Agent 实例在多个独立的 Docker 容器中动态拉起时，需要保证它们能够相互发现并进行消息路由。AutoGen 引入了 Agent 注册表（Registry）和服务发现网关。新拉起的远程 Agent 节点会自动向注册表注册其地址与所具备的 Capabilities，Orchestrator 可以根据任务类型通过网关动态将消息分发到不同的远程容器，避免了硬编码网络端口的碎片化问题。

#### 3. Hugging Face smolagents (多智能体工具委派与动态分派)
*   **核心创新一：智能体即工具封装 (Agents-as-Tools Interface)**
    *   *机制原理*：传统的多 Agent 交互（如 Swarm 的 handoff 或 CrewAI 的 task delegation）会把所有 Agent 放入同一个大的提示词/上下文空间中，导致 Token 消耗指数级上升，且容易产生跨角色指令污染。smolagents 引入了 `Agent-as-Tool` 范式。任何子 Agent（例如一个专门的 ACI 文件检索器，或 AST 语法检查器）都可以被直接包装成一个标准的 Python Tool 实例传给 Master CodeAgent。主 Agent 仅需使用标准的 Python 代码 `retriever_agent(query="find symbol X")` 来调用它。
*   **核心创新二：运行时参数校验与动态代码工具隔离 (Runtime Schema Enforcement & Isolated Code Context)**
    *   *机制原理*：子 Agent 内部的推理过程、局部变量、甚至是生成的 Python 代码，都在子 Agent 的独立沙盒/解析器中执行。只有最终的 string 或 JSON 返回值会被传递回 Master Agent 的上下文。这种物理和词法上的隔离保证了高层规划与底层执行的分离，有效限制了低层执行器的权限越权，并降低了 Master Agent 的提示词损耗。

```mermaid
graph TD
    subgraph LangGraph-DoubleLoop
        RunNode[Graph execution node] -->|Reach interrupt node| SaveSnap[Save state snapshot to Store]
        SaveSnap -->|Suspend execution| HITL[Human Intervention Gateway]
        HITL -->|Edit State Variables / Approve| Resume[Resume from state snapshot]
        Resume --> NextNode[Continue next node]
        NextNode -->|Error detected| TimeTravel[Rollback to historical snapshot]
        TimeTravel --> SaveSnap
    end
    subgraph AutoGen-v04-Distributed
        AgentHost1[Agent Container 1] -->|Register capability| Registry[Consul/gRPC Service Registry]
        AgentHost2[Agent Container 2] -->|Register capability| Registry
        Orchestrator[Orchestrator Agent] -->|Lookup registry & dispatch| Registry
        Orchestrator -->|Asynchronous Protobuf over gRPC| AgentHost1
        Orchestrator -->|Asynchronous Protobuf over gRPC| AgentHost2
    end
    subgraph smolagents-Agent-As-Tool
        Master[Master CodeAgent] -->|Write Python: sub_agent.run()| ToolWrap[SubAgent wrapped as standard Tool]
        ToolWrap -->|Run in isolated sandbox| SubAgent[SubAgent Worker]
        SubAgent -->|In-memory AST parse & execute| Actions[Execution context]
        Actions -->|Result string / json| Master
    end
```"""

# Split before the table begins
target_split = u"""        Context[Context docs / logs] & Answer[Agent Output / Report] -->|Split into assertions| Faith[Faithfulness Evaluator]
        Faith -->|Check Entailment| ScoreF[Faithfulness Score]
        Answer -->|Reverse questions| Rel[Answer Relevancy Evaluator]
        Rel -->|Embedding Similarity| ScoreR[Answer Relevancy Score]
    end
```"""

if target_split not in md_content:
    target_split = target_split.replace(u'\n', u'\r\n')

if target_split not in md_content:
    print("Error: Target split not found in markdown report.")
    sys.exit(1)

parts = md_content.split(target_split)
updated_md = parts[0] + target_split + u"\n\n---\n\n" + timeline_insert + u"\n" + target_split.join(parts[1:])

# Write updated Markdown
with io.open(report_md_path, "w", encoding="utf-8") as f:
    f.write(updated_md)
print("Successfully appended Round 24 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 24 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round18" class="nav-link">R18: LangGraph / AutoGen / smolagents</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 24
round24_html = u"""      <!-- Round 18 (24th Research) -->
      <section id="round18">
        <h2>R18：双向人机图中断回滚、分布式 gRPC 跨容器通信与多智能体工具委派 (LangGraph & AutoGen & smolagents)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LangGraph, AutoGen 与 smolagents 的高级拓扑与分发机制</span>
              <span class="product-meta">Double-loop rollback, distributed gRPC & Agent-as-Tool delegation</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LangGraph · 双向人机状态中断与时间旅行 (HITL & Time-Travel)</strong>：在图节点前后定义中断，支持人工介入并直接编辑状态变量，同时通过保留完整的状态快照树提供多步执行失败后的任意节点回滚（时间旅行），防止修复发散。</li>
              <li><strong>AutoGen v0.4 · 分布式 gRPC 远程智能体通信 (Distributed gRPC)</strong>：引入跨物理容器/主机的远程 Actor 运行时模型，所有协作消息基于 Protobuf 进行低延迟 gRPC 网络传输，结合服务发现机制进行动态路由，实现物理级别隔离。</li>
              <li><strong>smolagents · 智能体即工具封装与上下文隔离 (Agent-as-Tool)</strong>：支持将子智能体直接包装成 Master Agent 可以用 Python 代码调用的标准 Tool 实例，子 Agent 推理与运行环境词法隔离，彻底降低 Token 膨胀与指令污染。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 24 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round24_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 24 to open_source_research_report.html.")
