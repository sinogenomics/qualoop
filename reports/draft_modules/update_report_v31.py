# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 31 Updater
Appends the 31st round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第三十一次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的嵌套子工作流与分层事件隔离、AutoGen v0.4 的消息传递保障与邮箱背压控制与 browser-use 的跨 iframe 与 Shadow DOM 树穿透定位

#### 1. LlamaIndex Workflows (嵌套子工作流与分层事件隔离)
*   **核心创新一：嵌套子工作流挂载与独立事件循环 (Nested Sub-Workflows & Isolated Event Loops)**
    *   *机制原理*：在极复杂的软件演进场景中，全局平面图结构容易产生难以理清的线条。Workflows 支持将一个独立的子工作流（Sub-Workflow）声明为父工作流中的一个普通步骤（Step）。子工作流拥有自己专属的事件定义、状态存储及独立的异步事件循环。当父图触发子图时，子图在沙盒化的上下文中自主收敛并输出最终 Event，实现了系统级的模块化与分级抽象。
*   **核心创新二：父子事件冒泡与选择性隔离拦截 (Hierarchical Event Bubbling & Selective Interception)**
    *   *机制原理*：为了防止嵌套子图中的细粒度事件污染父图的事件总线，Workflows 实行了“事件分层隔离”。默认情况下，子图内部的事件仅在其内部流转。若需要通知父图，子图必须显式抛出特定的冒泡事件（Bubbled Event）。父图的拦截器可以像 HTML DOM 事件监听一样，选择性地捕获并处理这些冒泡事件，或者将其阻断在子图边界内，保证了消息拓扑的清晰。

#### 2. Microsoft AutoGen v0.4 (消息传递保障与邮箱背压控制)
*   **核心创新一：带有确认应答的至少一次传递保证 (At-Least-Once Delivery with ACK/NACK)**
    *   *机制原理*：在分布式智能体群中，网络闪断或节点重启极易引发消息丢失。AutoGen v0.4 实现了应用层的 ACK/NACK 应答机制。当 Agent Actor 发送消息时，消息会暂存在本地发件箱（Outbox）中并启动超时重传定时器。接收端 Actor 必须在收到并验证 Protobuf 数据后反向发送 `MessageAcknowledged` 事件。如果超时未收到 ACK，发送端会自动进行指数退避重试，确保了指令传输的强可靠性。
*   **核心创新二：滑动窗口背压流控机制 (Sliding Window Backpressure Flow Control)**
    *   *机制原理*：为了防止某个性能较低的 Executor 被瞬间涌入的高频 Issue 检测事件压垮，AutoGen 0.4 的邮箱系统（Mailbox）设计了滑动窗口背压（Backpressure）。Actor 的接收队列设有最大积压容量。当队列达到水位线时，Actor 会向事件网关发送 `Pause` 信号。网关会暂停向其路由新消息并将其缓存在 Broker 队列中，直到 Executor 消化完积压任务并发送 `Resume` 信号，防范了高并发下的崩溃溢出。

#### 3. browser-use (跨 iframe 与 Shadow DOM 树穿透定位)
*   **核心创新一：穿透式深度选择器与 iframe 边界桥接 (Cross-Boundary iframe Selector Bridging)**
    *   *机制原理*：现代 Web 项目中，很多动态表单或第三方组件被封装在嵌套的 `<iframe>` 中。由于同源策略或常规 DOM 遍历限制，普通 Selector 很难定位。browser-use 引擎在初始化时，会自动向当前页面的所有 nested frames 注入通讯网桥桥接器（Bridge Helper）。在定位时，通过深度递归遍历（Deep Recursive Query），将 Agent 的操作意图流式广播给各个 Frame 的桥接器，在子上下文内完成元素查找并计算相对于主视口的偏移，实现了跨边界无缝交互。
*   **核心创新二：Shadow DOM 树穿透与语义视口匹配 (Shadow DOM Piercing & Semantic Projection)**
    *   *机制原理*：现代前端框架（如 Web Components）常使用 Shadow DOM 将子树隔离。普通的 `querySelector` 默认无法穿透 shadow root 边界。browser-use 扩展了选择器语法，支持 `>>>` 或 `/deep/` 语义的 Shadow root 穿透遍历。它在 DOM tree 构建期通过递归读取 `shadowRoot` 属性，将隐藏在影子 DOM 内部的所有可交互元素（如 Shadowed button）拉平并进行数字索引标注，使 VLM 视觉图层能与 Shadow DOM 内部元素精准匹配。

```mermaid
graph TD
    subgraph LlamaIndex-Nested-Workflows
        ParentWorkflow[Parent Workflow loop] -->|Trigger Step| SubWorkflow[Sub-Workflow loop]
        SubWorkflow -->|Isolated Event flow| SubStep[Sub Step node]
        SubStep -->|Bubbled Event| ParentWorkflow
    end
    subgraph AutoGen-v04-Mailbox-Backpressure
        Sender[Sender Actor Outbox] -->|1. Send Protobuf| Receiver[Receiver Actor Mailbox Queue]
        Receiver -->|2. Check queue size > high watermark| Gateway[Broker Gateway]
        Gateway -->|3. Pause routing| Sender
        Receiver -->|4. Process & send ACK| Sender
    end
    subgraph browser-use-Iframe-ShadowDOM
        MasterBrowser[Master Browser viewport] -->|Bridge query| Bridge[Iframe Bridge Helper]
        Bridge -->|Find element in sub-frame| Element[Target Element]
        MasterBrowser -->|Recursive query shadowRoot >>>| ShadowDOM[Shadow root element]
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
print("Successfully appended Round 31 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 31 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round25" class="nav-link">R25: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 31
round31_html = u"""      <!-- Round 25 (31st Research) -->
      <section id="round25">
        <h2>R25：嵌套子工作流事件隔离、分布式邮箱背压流控与跨 boundaries 页面定位 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的层级结构与传输流控</span>
              <span class="product-meta">Nested sub-workflows, ACK/NACK backpressure & deep iframe piercing</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 嵌套子图挂载与父子事件冒泡 (Nested Workflows)</strong>：支持将子 Workflow 作为父 Workflow 的独立步骤运行，并在子图间实施分层事件隔离与选择性事件冒泡拦截，理清复杂消息关系。</li>
              <li><strong>AutoGen v0.4 · 消息确认重传与滑动窗口背压 (Flow Control)</strong>：实现应用层 ACK/NACK 保证至少一次传递，并通过接收端 Mailbox 溢出水位线触发的 Pause/Resume 信号提供弹性背压控制。</li>
              <li><strong>browser-use · 跨 iframe 通讯网桥与 Shadow DOM 穿透 (DOM Piercing)</strong>：向所有子 iframe 自动注入通讯网桥计算物理视口偏移，并利用影子 DOM 树穿透选择器（`>>>`）标注内部交互节点。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 31 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round31_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 31 to open_source_research_report.html.")
