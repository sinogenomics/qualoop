# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 36 Updater
Appends the 36th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第三十六次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的事件驱动型确定性状态机转换、AutoGen v0.4 的分布式 ProtoBuf 事件发布与订阅广播与 browser-use 的运行时自定义工具与 JS 函数动态挂载

#### 1. LlamaIndex Workflows (事件驱动型确定性状态机转换)
*   **核心创新一：基于强类型事件的确定性状态转移 (Deterministic State Transitions via Strong-typed Events)**
    *   *机制原理*：传统状态机在定义状态转移（Transitions）时，需要维护复杂的全局转移矩阵或静态路由图，而在高并发环境下这容易产生路由冲突。LlamaIndex Workflows 提供了纯事件驱动的确定性状态机模型。每个状态被定义为一个接收特定输入事件并射出特定输出事件的节点，状态转移完全由总线中分发的强类型事件驱动，这在不依赖显式状态图的前提下实现了拓扑流向的严格确定性。
*   **核心创新二：动态事件路由选择与步骤多态性 (Polymorphic Step Event Routing)**
    *   *机制原理*：当系统需要根据同一个输入事件（如 `IssueDetectedEvent`）触发不同类型的分析节点（如 Linter 还是 SecurityCheck）时，Workflows 支持基于多态的事件分发。事件类可以被子类化，步骤节点可以通过订阅特定的事件子类，实现动态的路由分配和步骤多态，这在复杂的自愈决策中提供了极高的灵活性。

#### 2. Microsoft AutoGen v0.4 (分布式 ProtoBuf 事件发布与订阅广播)
*   **核心创新一：基于 gRPC 的分布式 Pub/Sub 事件通道 (gRPC-backed Distributed Pub/Sub Channels)**
    *   *机制原理*：在多物理节点分布的多智能体系统中，为了实现全局广播（如发布全局 North Star 变更或紧急关闭信号），需要高效的广播媒介。AutoGen v0.4 实现了基于 gRPC 和 ProtoBuf 的分布式 Pub/Sub 事件发布与订阅机制。智能体可以动态向特定的事件主题（Topic）进行注册，消息以二进制 ProtoBuf 进行串行流式传输，实现了低延迟的分布式广播。
*   **核心创新二：动态订阅组管理与分布式负载均衡分发 (Dynamic Subscription Group & Load Balancing)**
    *   *机制原理*：当大批 Executor 实例并发加入系统并订阅相同的修复任务事件时，Pub/Sub 通道支持动态订阅组（Subscription Groups）管理。注册网关会自动识别组内成员的活性，并使用一致性哈希或轮询策略对广播的事件消息进行分发，防止消息被重复消费，并保证了集群高并发分发下的整体吞吐量。

#### 3. browser-use (运行时自定义工具与 JS 函数动态挂载)
*   **核心创新一：浏览器上下文自定义 Tool 动态挂载 (Dynamic Tool Registration in Browser Context)**
    *   *机制原理*：常规的浏览器自动化只提供 click、type 等原生基础交互工具，而面对复杂的业务校验（如提取页面图表数据或进行特定的接口防重放模拟），基础工具显得过于冗长。browser-use 支持在运行时向 Agent 动作空间（Action Space）动态注册自定义的 Python 逻辑或 API。Agent 在推理时，可以直接调用 `custom_tool(name="calc_financial_matrix")`，由引擎在本地解析执行并返回，显著拓宽了 Tester 的验证边界。
*   **核心创新二：安全沙箱化的 JS 函数运行时注入与评估 (Sandboxed JS Injection and Evaluation)**
    *   *机制原理*：在动态页面测试中，常常需要向当前 DOM 树中注入并执行复杂的 JS 脚本以验证底层变量状态。browser-use 提供了安全的 JS 注入与评估引擎（JS Execution Sandbox）。引擎通过 Playwright 的底层虚拟执行边界，将大模型生成的 JS 脚本限制在完全只读和非特权的沙盒边界内运行，获取页面隐藏变量后安全反序列化返回，杜绝了注入恶意脚本导致宿主机被反向劫持的物理风险。

```mermaid
graph TD
    subgraph LlamaIndex-State-Transitions
        EventBus[Event Bus] -->|Emit IssueDetectedEvent| StepA[Step A: parse issue]
        StepA -->|Emit FixRequiredEvent| StepB[Step B: execute fix]
        StepB -->|Emit VerifyRequiredEvent| StepC[Step C: run tests]
        EventBus -.->|Dynamic Polymorphic Routing| StepA
    end
    subgraph AutoGen-v04-Distributed-PubSub
        Topic[Event Topic: NorthStarChanges] -->|gRPC Streams| MemberA[Distributed Agent Actor A]
        Topic -->|gRPC Streams| MemberB[Distributed Agent Actor B]
        Topic -->|Load Balanced| Group[Subscription Group / Executor Replicas]
    end
    subgraph browser-use-DynamicTools
        MasterAgent[Master Agent] -->|Call custom_tool| NativeEngine[Browser-use Engine]
        NativeEngine -->|Inject read-only JS| JSSandbox[JS Execution Sandbox]
        JSSandbox -->|Fetch variables| DOM[DOM Window State]
        DOM -->|Safely return values| MasterAgent
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
print("Successfully appended Round 36 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 36 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round30" class="nav-link">R30: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 36
round36_html = u"""      <!-- Round 30 (36th Research) -->
      <section id="round30">
        <h2>R30：确定性事件状态转移、gRPC 事件广播订阅与浏览器自定义工具注入 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的状态控制与自定义扩展</span>
              <span class="product-meta">State transitions, distributed pub/sub & browser dynamic JS execution</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 强类型事件驱动确定性状态机 (Polymorphic Routing)</strong>：利用纯强类型事件发射与订阅，不依赖显式路由图定义，实现了逻辑状态的确定性转移与步骤多态。</li>
              <li><strong>AutoGen v0.4 · 分布式 gRPC 二进制 Pub/Sub 事件总线 (ProtoBuf PubSub)</strong>：引入基于 gRPC 流式 ProtoBuf 的发布/订阅广播机制，支持动态订阅组及分布式一致性路由负载均衡分发。</li>
              <li><strong>browser-use · 运行时自定义工具注册与沙箱化 JS 函数注入 (JS Sandbox)</strong>：支持向 Action Space 动态挂载局部的自定义 Python/API 动作，并在只读非特权的 JS 沙盒环境中安全解析获取页面底层变量。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 36 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round36_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 36 to open_source_research_report.html.")
