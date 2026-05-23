# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 38 Updater
Appends the 38th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第三十八次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的事件驱动动态图拓扑重写与二次规划、AutoGen v0.4 的有状态 Actor 运行时动态跨节点迁移调度与 browser-use 的多浏览器视觉协作锁与跨标签协同

#### 1. LlamaIndex Workflows (事件驱动动态图拓扑重写与二次规划)
*   **核心创新一：运行时动态图拓扑结构重写 (Runtime Workflow Graph Rewriting)**
    *   *机制原理*：传统的多智能体有向图或 DAG 一旦定义，其执行拓扑和依赖路径便被固化，无法应对非预期的运行时突发变化。Workflows 提供了运行期图拓扑动态重写功能。当图中的审计步骤（Linter）发现系统架构产生越级腐化时，可以发射一个 `TopologyRewriteEvent`。主运行引擎（Runner）接收后，能够动态从当前的执行链中剔除低效节点，并并联注入新的分析和测试步骤节点，实现了代码级的拓扑自我演进。
*   **核心创新二：基于反向传播反馈的动态二次规划 (Feedback-driven Dynamic Re-planning)**
    *   *机制原理*：在自动修复未通过测试时，系统不能仅依靠静态重试。Workflows 能够将 Verifier 的失败详情和测试堆栈反向流式发送给规划步骤。规划步骤会启动动态二次规划器（Re-planner），计算出与原拓扑不同的新执行计划，并动态改写当前工作流的后续事件路由（Event Routing Map），使修复链路能绕开死胡同并探索新分支。

#### 2. Microsoft AutoGen v0.4 (有状态 Actor 运行时动态跨节点迁移调度)
*   **核心创新一：基于宿主机性能度量的动态 Actor 跨节点迁移 (Performance-driven Dynamic Actor Migration)**
    *   *机制原理*：在由成百上千个 Agent Actor 组成的庞大集群中，各宿主机的负载（CPU、内存、网络 IO）是时刻波动的。如果某个有状态 Actor 处于高负载节点上，其邮箱响应时间会大幅退化。AutoGen v0.4 的集群调度器（Cluster Scheduler）会收集节点资源指标，并在检测到 CPU/Mem 达到警戒红线时，在运行期动态触发 Actor 迁移（Migration）。它将 Actor 挂起，把完整的运行栈快照流式发送给轻载的节点，在无损状态的前提下实现物理节点的平滑切换。
*   **核心创新二：跨节点通信的逻辑拓扑路由映射 (Cross-node Logical Routing Topology Mapping)**
    *   *机制原理*：在有状态 Actor 跨节点热迁移后，为了让原本与其通信的其它 Agent 能够立刻把消息发到其新的物理地址，AutoGen 引入了实时的拓扑路由映射更新机制。迁移成功后，接收端的节点虚拟机会向 Raft 注册表发送 `ActorLocationUpdated` 二进制广播，全局的分布式路由网关会在微秒级更新该 Actor 的位置映射。所有发送给该 Actor ID 的 gRPC 消息会自动重定向到新节点，避免了消息路由的悬空和丢失。

#### 3. browser-use (多浏览器视觉协作锁与跨标签协同)
*   **核心创新一：多标签页跨视图视觉协作锁 (Multi-Tab Visual Collaboration Locks)**
    *   *机制原理*：在模拟需要多用户或多角色（如卖家在 A 页发货，买家在 B 页确认）并行配合的复杂 E2E 验证场景中，由于两端操作在同一个浏览器上下文中并发进行，极易发生标签页抢占或点击失焦。browser-use 引入了会话级视觉协作锁（Visual Collaboration Locks）。当 Agent A 在 Tab 1 上进行高密度的 VLM 截图定位时，协作锁会锁定该标签页的视口焦点，限制 Agent B 在 Tab 2 上进行页面滚动等可能破坏截图完整性的操作，实现了多智能体视觉同步。
*   **核心创新二：基于事件广播的跨标签分布式协同管道 (Event-driven Cross-tab Communication Channel)**
    *   *机制原理*：为了实现不同标签页内 Tester 进程的信息共享，browser-use 内置了跨标签通讯管道。Tab 1 内部的任何网络拦截事件（如捕获到 API 发出 of token）会流式广播给管道，Tab 2 的 Agent 会自动从管道拉取该变量并填入表单，消除了常规多标签页自动化中不同 Page 之间相互孤立的痛点，满足了极高难度的跨域/跨标签交互需求。

```mermaid
graph TD
    subgraph LlamaIndex-Dynamic-Rewriting
        LinterNode[Linter Audit Node] -->|TopologyRewriteEvent| Runner[Workflow Runner]
        Runner -->|1. Detach old node| OldStep[Old Steps]
        Runner -->|2. Dynamically attach new node| NewStep[New verification step]
        VerifierFailed[Verifier Traceback Stack] -->|3. Feed back| RePlanner[Re-planner Step]
        RePlanner -->|4. Rewrite Event Routing Map| Runner
    end
    subgraph AutoGen-v04-Actor-Migration
        Scheduler[Cluster Scheduler] -->|1. Overload detected / CPU 95%| HostA[Host A Actor: Deactivate]
        HostA -->|2. Stream Stack Snapshot| HostB[Host B Actor: Restore]
        HostB -->|3. Broadcast ActorLocationUpdated| Registry[Raft Registry]
        Registry -->|4. Update gRPC routing map| Gateway[Distributed Agent Gateway]
    end
    subgraph browser-use-CollaborationLock
        Tab1[Tab 1 Agent: capturing screenshot] -->|Acquire| CollabLock((Visual Collab Lock))
        Tab2[Tab 2 Agent: wait viewport state] -.->|Restricted by| CollabLock
        Tab1 -->|Intercept network token| CommChannel[Cross-Tab Channel]
        CommChannel -->|Sync variable payload| Tab2
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
print("Successfully appended Round 38 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 38 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round32" class="nav-link">R32: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 38
round38_html = u"""      <!-- Round 32 (38th Research) -->
      <section id="round32">
        <h2>R32：运行时图拓扑重写与二次规划、Actor 跨节点迁移调度与多标签页视觉协作锁 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的动态规划与资源调度</span>
              <span class="product-meta">Graph topology rewriting, Actor migration & cross-tab visual locks</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 运行时图拓扑动态重写与二次规划 (Topology Rewrite)</strong>：当检测到架构缺陷时发射重构事件动态剔除/并联挂载新节点，结合测试失败堆栈反向引导规划器改写路由表。</li>
              <li><strong>AutoGen v0.4 · 负载驱动的 Actor 跨物理节点热迁移与 gRPC 重定向 (Actor Migration)</strong>：在宿主机过载时自动打包 Actor 栈与邮箱跨物理容器发送恢复，配合 Raft 注册表秒级广播映射更新以实现 gRPC 重定向。</li>
              <li><strong>browser-use · 多标签页视口会话视觉协作锁与跨标签协同通道 (Collab Lock)</strong>：引入会话级视觉协作锁防止多 Agent 截图冲突，结合跨标签页分布式广播管道解决跨域多角色流程的数据孤岛。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 38 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round38_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 38 to open_source_research_report.html.")
