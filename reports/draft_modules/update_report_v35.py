# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 35 Updater
Appends the 35th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第三十五次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的步骤执行超时看门狗与条件事件自愈、AutoGen v0.4 的分布式 Actor 集群节点状态心跳同步与 browser-use 的浏览器多上下文 Session 会话持久化与状态重放

#### 1. LlamaIndex Workflows (步骤执行超时看门狗与条件事件自愈)
*   **核心创新一：步骤级超时看门狗 (Step-level Execution Timeout Watchdog)**
    *   *机制原理*：在复杂的自愈循环中，某一步骤（如拉起测试或调用 LLM）可能会由于环境死锁或网络丢包而无限期挂起，导致整个图阻塞。Workflows 提供了步骤级的执行超时机制。开发者可以为特定的 `@step` 节点声明 `timeout` 阈值。如果该步骤的异步协程在此时间内未 Resolved，工作流引擎会自动打断该协程，发射一个强类型的 `StepTimeoutEvent`，并传递给备用自愈节点，实现了单点故障在图层级的自动隔离。
*   **核心创新二：动态条件事件自愈路由 (Dynamic Conditional Self-healing Routing)**
    *   *机制原理*：传统状态机遇到超时或失败往往直接报错。Workflows 基于纯事件订阅，可以挂载通用的自愈路由器（Self-healing Router）。当捕获到 `StepTimeoutEvent` 或 `StepFailedEvent` 时，自愈节点会根据错误发生的历史次数和错误上下文，动态构建包含回滚指令的自愈事件（如 `RetryWithFallbackEvent`）并重新注入总线，引导工作流退避切换到备用大模型或本地 AST 执行沙盒，完成了工作流的弹性自愈闭环。

#### 2. Microsoft AutoGen v0.4 (分布式 Actor 集群节点状态心跳同步)
*   **核心创新一：基于 gRPC 心跳通道的节点状态活性检测 (gRPC-backed Heartbeat Active Detection)**
    *   *机制原理*：在跨容器/主机分布的智能体集群中，远程的 Executor Actor 随时可能因为容器 OOM 或网络中断而下线。AutoGen v0.4 的节点注册中心（Registry）与各个 Actor 节点之间建立双向的 gRPC 心跳监听流（Heartbeat Streams）。节点以百毫秒级高频发送心跳包，一旦注册中心在连续 3 个心跳周期内未收到某节点的应答，会自动将该 Actor 的状态标记为 `Unreachable`，为任务重分派提供快速感知。
*   **核心创新二：分布式哈希环一致性路由与故障接管 (Distributed Consistent Hash Ring & Failover)**
    *   *机制原理*：为了实现任务的无损接管，集群引入了一致性哈希环（Consistent Hash Ring）拓扑。每个 Actor 节点在环上占据物理分片。当某个节点被心跳机制判定为不可达时，路由网关会自动顺时针寻找环上的下一个备用可用节点，将属于故障节点的所有待处理 Issue 与 mailbox 邮件热路由迁移过去，避免了分布式环境下任务的死锁与丢失。

#### 3. browser-use (浏览器多上下文 Session 会话持久化与状态重放)
*   **核心创新一：多租户浏览器会话快照与反序列化 (Multi-tenant Session Snapshotting)**
    *   *机制原理*：在自动 Tester 对需要登录权限的系统进行长周期跑测时，如果每次启动沙盒都要引导 Agent 重新执行一遍扫码或拖动验证码登录，不仅效率极低，而且极易触发网站的安全风控导致测试失败。browser-use 原生支持对独立的 Browser Context 进行完整的状态快照（Session Snapshotting）。它将当前的 Cookie 列表、LocalStorage 数据库、SessionStorage 键值对序列化为统一的 JSON 文件并存盘。新拉起的沙盒只需一键加载该 JSON，即可“瞬间恢复”到已登录的活跃会话中，极大地提高了长周期验证的流畅度。
*   **核心创新二：IndexedDB 本地数据库状态归档与状态重放 (IndexedDB Storage Snapshotting)**
    *   *机制原理*：对于现代单页应用（SPA），大量的核心业务状态（如草稿箱、离线缓存数据）是存储在浏览器的 IndexedDB 数据库中的。简单的 Cookie 快照无法还原这部分数据。browser-use 在会话快照时，会注入专门的安全脚本读取并将 IndexedDB 的结构与记录序列化存盘。在重放测试或换沙盒执行时，能够一并重构 IndexedDB 数据库结构并导入数据，确保了多模态 Tester 的运行状态高精度复现。

```mermaid
graph TD
    subgraph LlamaIndex-Step-Timeout
        Step[Long Running Step Node] -->|Timeout exceeded| Watchdog[Timeout Watchdog Timer]
        Watchdog -->|Interrupt Step & Emit| TimeoutEvent[StepTimeoutEvent]
        TimeoutEvent -->|Route to| FallbackRouter[Self-Healing Router]
        FallbackRouter -->|Generate RetryEvent| EventBus[Event Bus Loop]
    end
    subgraph AutoGen-v04-Heartbeat
        Registry[Registry / Orchestrator] <-->|gRPC Heartbeat streams| ActorNode[Actor Node in Container]
        Registry -->|Miss 3 heartbeats: mark unreachable| Ring[Consistent Hash Ring]
        Ring -->|Reroute Mailbox messages| BackupNode[Backup Actor Node / Failover]
    end
    subgraph browser-use-SessionStore
        Playwright[Playwright Sandbox Browser] -->|Serialize context| Snapshot[Session Snapshot JSON]
        Snapshot -->|Include Cookies & LocalStorage| Snapshot
        Playwright -->|Inject script to serialize| IndexedDB[IndexedDB JSON dump]
        Snapshot & IndexedDB -->|Load in new Context| NewSandbox[New Restored Browser Context]
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
print("Successfully appended Round 35 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 35 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round29" class="nav-link">R29: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 35
round35_html = u"""      <!-- Round 29 (35th Research) -->
      <section id="round29">
        <h2>R29：执行超时看门狗与自愈路由、Actor 集群哈希一致路由与浏览器 IndexedDB 会话快照 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的故障隔离与会话快照机制</span>
              <span class="product-meta">Step watchdogs, consistent hash failover & IndexedDB context restoration</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 步骤超时中断与动态自愈路由 (Timeout Watchdog)</strong>：支持为节点设置毫秒级超时定时器自动打断阻塞协程并发射超时事件，引导自愈路由器切换回滚至备用沙盒。</li>
              <li><strong>AutoGen v0.4 · gRPC 双向心跳检测与哈希环一致路由接管 (Hash Ring Failover)</strong>：基于 gRPC 心跳包快速检测故障节点并更新活性状态，配合一致性哈希环路由自动无损迁移 mailbox 邮件与修复任务。</li>
              <li><strong>browser-use · 浏览器 LocalStorage 与 IndexedDB 结构化会话快照 (IndexedDB Snapshot)</strong>：在不打扰安全审计的前提下一键序列化 Cookies、本地存储及 IndexedDB 记录并在新沙盒秒级反序列化重建，实现会话保活。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 35 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round35_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 35 to open_source_research_report.html.")
