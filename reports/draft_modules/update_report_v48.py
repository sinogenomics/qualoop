# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 48 Updater
Appends the 48th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第四十八次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的多事件动态汇聚与步骤重新同步、AutoGen v0.4 的 Actor 去中心化集群发现与 Gossip 节点成员管理、browser-use 的 Shadow DOM 与嵌套 Iframe 穿透定位器

#### 1. LlamaIndex Workflows (多事件动态汇聚与步骤重新同步)
*   **核心创新一：声明式多事件动态汇聚机制 (Dynamic Multi-Event Joining)**
    *   *机制原理*：在并行化智能体协作中，某个决策节点通常必须收集到多个独立分支的前置计算结果（例如，翻译步骤必须同时等到“译文审核结果”和“术语表匹配完成”两个事件）后才能触发。Workflows 提供了一种声明式的多事件汇聚器（Dynamic Joiner）。它允许某个 Step 通过 `@step(pass_events=[EventA, EventB])` 声明其依赖的事件数组。引擎运行时会自动在内部的状态管理器中维护针对当前 Context ID 的事件收集进度。
*   **核心创新二：暂存缓冲与事件合并驱动 (Stateful Event Merging & Resynchronization)**
    *   *机制原理*：当依赖的部分事件先到达时，引擎会在内存数据库中将其暂存缓冲。一旦声明依赖的所有事件都集齐，事件合并驱动器（Event Merger）会自动将多个前置事件的数据载荷（Payloads）打包，并在当前协程上下文中重新同步（Resynchronize）并调度唤醒该 Step 节点，从而避免了多分支并发下的乱序与竞争状态。

#### 2. Microsoft AutoGen v0.4 (Actor 去中心化集群发现与 Gossip 节点成员管理)
*   **核心创新一：基于 Gossip 协议的去中心化集群发现 (Gossip-based Peer Discovery)**
    *   *机制原理*：随着集群规模动态扩张，如果所有 Actor 实例的在线状态和路由节点信息都高频向一个单一的中心数据库注册表读写，会成为严重的系统单点瓶颈。AutoGen v0.4 引入了去中心化的 Gossip 协议。新加入的物理节点只需与几个初始种子节点（Seed Peers）进行握手，之后有关新节点、死亡节点以及 Actor 分布的元数据就会以 Gossip（传闻）机制在物理节点拓扑中快速广播，实现了无中心的自发现。
*   **核心创新二：动态路由表 Gossip 同步与存活检测 (Dynamic Gossip Routing Map)**
    *   *机制原理*：每个物理节点在本地缓存一份全局 Actor 路由表。Gossip 引擎通过定期的“Ping-Pong”探针与对等节点交换路由表哈希和序列号。如果检测到某个邻近节点的心跳丢失超过预设阈值（例如 3 秒），会判定该节点下线，并将该离线状态标记广播出去，本地动态路由表随即更新以将消息路由重定向到健康副本，确保了集群的可伸缩性与容错能力。

#### 3. browser-use (Shadow DOM 与嵌套 Iframe 穿透定位器)
*   **核心创新一：基于 DOM Deep-Query 的 Shadow 边界穿透定位 (Shadow DOM Boundary Piercing)**
    *   *机制原理*：现代前端框架（如 Web Components, Lit, Salesforce Lightning）为了实现样式组件的完美封装，广泛采用了 Shadow DOM 技术。Shadow Root 内部的 DOM 树对标准的 Playwright 或 WebDriver 定位选择器是完全隐藏的，导致传统的 CSS/XPath 定位完全失效，Agent 因无法定位按钮而测试失败。browser-use 通过在浏览器页面中注入定制的深度查询脚本，利用 `element.shadowRoot` 属性递归穿透每一层 shadow 边界，精准暴露并获取目标组件的真实引用。
*   **核心创新二：递归跨 iframe 上下文切换与穿透 (Recursive Nested Iframe Traversing)**
    *   *机制原理*：对于更复杂的第三方插件或嵌入式报表，页面可能嵌套多层 `iframe` 容器。普通的测试工具需要繁琐地手动调用切换 frame 上下文的 API。browser-use 实现了自适应的穿透定位引擎。当定位器目标处于某个深层 `iframe` 内部时，引擎自动解析其 DOM 层级路径，递归地遍历并进入对应的 iframe FrameContext，获取相对于主文档的坐标和焦点，使得智能体可以像操作原生元素一样点击或输入。

```mermaid
graph TD
    subgraph LlamaIndex-Dynamic-Join
        EventA[Event A Arrived] -->|Store in memory db| Joiner[Dynamic Event Joiner]
        EventB[Event B Arrived] -->|Store in memory db| Joiner
        Joiner -->|1. Check dependencies: EventA & EventB| StatusCheck{All events collected?}
        StatusCheck -->|No| KeepWaiting[Keep waiting in store]
        StatusCheck -->|Yes| Merger[Event Merger]
        Merger -->|2. Pack combined payload & wake step| TargetStep[Joined Target Step]
    end
    subgraph AutoGen-Gossip-Discovery
        NodeNew[New Node C] -->|1. Gossip Seed Handshake| SeedNode[Seed Node A]
        SeedNode -->|2. Spread membership state| NodeB[Node B]
        NodeNew & NodeB & SeedNode -->|3. Local Routing Table Sync| Gossip[Gossip Protocol Engine]
        Gossip -->|4. Peer heartbeats ping/pong| DeadCheck{Dead Peer detected?}
        DeadCheck -->|Yes| UpdateRoute[Update route map: Evict dead node]
    end
    subgraph browser-use-Shadow-Pierce
        Agent[Test Agent Selector] -->|Deep click selector| PierceEngine[Shadow/Iframe Pierce Engine]
        PierceEngine -->|1. Traverse element.shadowRoot| ShadowRoot[Shadow Boundary]
        PierceEngine -->|2. Traverse nested frames| Iframe[Recursive Iframe Traversal]
        Iframe -->|3. Map deep physical coordinates| PageElement[Target Web Element]
        PageElement -->|4. Direct input/action injection| Action[Perform action]
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
print("Successfully appended Round 48 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 48 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round42" class="nav-link">R42: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 48
round42_html = u"""      <!-- Round 42 (48th Research) -->
      <section id="round42">
        <h2>R42：声明式多事件汇聚重同步、Gossip去中心集群发现与 Shadow DOM Iframe 递归穿透 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的汇聚与穿透机制</span>
              <span class="product-meta">Event dynamic join, Gossip routing & Shadow DOM piercing</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 声明式多事件动态汇聚与载荷重新同步 (Dynamic Join)</strong>：在内存中暂存未到齐事件，一旦依赖的所有事件全部集齐，自动打包数据并重同步拉起决策 Step。</li>
              <li><strong>AutoGen v0.4 · Gossip 协议无中心集群自发现与心跳自愈路由 (Gossip Routing)</strong>：摆脱中心化数据库依赖，利用 Gossip 机制传播集群在线成员信息，失联节点自动从本地路由表中下线剔除。</li>
              <li><strong>browser-use · Shadow DOM 封装边界深度查询与嵌套 Iframe 递归遍历 (Deep Locator)</strong>：使用注入式 JavaScript 脚本深度穿透 element.shadowRoot 和 iframe FrameContext，实现穿透式的精细定位。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 48 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round42_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 48 to open_source_research_report.html.")
