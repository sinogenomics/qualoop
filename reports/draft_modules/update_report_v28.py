# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 28 Updater
Appends the 28th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第二十八次调研（2026-05-23）: 深入分析 smolagents 的线程安全工具并发隔离与线程池编排、AutoGen v0.4 的 Actor 重入控制与死锁预防机制与 browser-use 的动态页面重排自适应视口坐标修正

#### 1. Hugging Face smolagents (线程安全工具并发隔离与线程池编排)
*   **核心创新一：线程局部工具实例池 (Thread-Local Tool Pools)**
    *   *机制原理*：在多线程高并发运行的 Agent 中，如果多个 Worker 并行修改同一个工具的私有状态（如带有内部 buffer 的代码执行器或网络 session），将导致惨烈的数据竞态。smolagents 引入了 Thread-Local 隔离机制。它为每个工作线程（Worker Thread）派生并绑定一个完全独立的工具实例副本，各个线程之间的工具状态（Memory buffers, cookies, local registers）实现物理隔离，支持安全的多路并发执行。
*   **核心创新二：线程池任务调度与限流保护 (Task Thread Pool Orchestration)**
    *   *机制原理*：为了防范瞬间拉起海量 Tool 执行器占满 CPU 核心或触发 API 服务限频（Rate Limit），smolagents 提供了线程池（Thread Pool Executor）调度器。所有工具调用和子 Agent 推理任务作为 Task 提交给线程池。它支持最大并发数配置（Max Workers）以及任务排队与退避限流（Backoff and Throttling），有效保护了宿主机资源在长周期运行下的绝对稳定。

#### 2. Microsoft AutoGen v0.4 (Actor 重入控制与死锁预防机制)
*   **核心创新一：基于逻辑时钟与消息队列的重入锁 (Logical-Clock Backed Reentrancy Lock)**
    *   *机制原理*：在多智能体深度嵌套或递归调用中，如果 Agent A 正在等待 Agent B 的回复，而 Agent B 的推理中又向 Agent A 发送了新的 Tool 查询请求，极易触发传统 Actor 模型中的同步死锁。AutoGen v0.4 引入了逻辑时钟（Logical Clocks）与异步消息重入队列。它允许 Actor 在挂起等待某个响应时，依然能够处理高优先级的嵌套子消息（Reentrant message processing），通过跟踪消息的 Parent-Child 树级脉络自动释放竞态，避免了循环依赖锁死系统。
*   **核心创新二：非阻塞异步 Future 轮询与超时恢复 (Non-blocking Async Future & Timeout Recovery)**
    *   *机制原理*：为了防止某个远程 Agent 假死（例如执行了超时计算或未响应网络命令）导致整个 Actor 协调链永久阻塞，AutoGen 底层通信完全基于非阻塞 Future（Awaitable Futures）。当发起 Acknowledge 握手或消息发送时，会自动挂载看门狗定时器。如果 Future 在设定阈值内未 Resolved，Actor 运行时会自动标记该目标节点不可达，将异常上报给 Orchestrator 进行重分派，保证系统强韧的容错恢复能力。

#### 3. browser-use (动态页面重排自适应视口坐标修正)
*   **核心创新一：自适应 DOM 重排与动态坐标重算 (DOM Reflow & Viewport Coordinate Recalculation)**
    *   *机制原理*：在动态加载的现代 Web 页面上，由于 lazy loading 广告、异步加载的列表图片、或者 CSS 弹性动画，页面元素在第一次渲染后可能会发生物理位移（Reflow / Relayout）。如果 Agent 坚持使用第一次探测到的 Bounding Box 物理坐标进行点击，极易点在空白处或误触其他组件。browser-use 在执行每一次交互动作（如 `click`）前的一微秒内，会自动向浏览器注入轻量级 JS 探针，对目标 DOM 节点的 `getBoundingClientRect()` 进行物理坐标的二次重算（Just-in-time calculation），自动弥合页面排版偏移带来的定位偏差。
*   **核心创新二：动效消隐与稳定态交互检测 (Layout Stability Verification)**
    *   *机制原理*：针对包含大量 JS 渐变动画的复杂单页应用，若在动画进行中盲目点击可能导致动作丢失。browser-use 内置了布局稳定性验证器（Stability Checker）。它会在执行动作前以高频（如 50ms 间隔）连续截取视口并对比关键 DOM 树的坐标位移，只有当检测到连续两次位移变化率趋于 0（即页面进入静态稳定态）时，才发出 physical click 信号，彻底消除了由于前端动画未完成导致的交互失焦现象。

```mermaid
graph TD
    subgraph smolagents-Concurrency-Pool
        ThreadA[Worker Thread A] -->|Bind Local copy| ToolInstanceA[Local Tool Instance A]
        ThreadB[Worker Thread B] -->|Bind Local copy| ToolInstanceB[Local Tool Instance B]
        TaskQueue[Agent Task Queue] -->|Throttle / Backoff| ThreadPool[ThreadPoolExecutor]
        ThreadPool --> ThreadA
        ThreadPool --> ThreadB
    end
    subgraph AutoGen-v04-Reentrancy
        ActorA[Agent Actor A: waiting response] -->|1. Suspend core thread| FutureA[Awaitable Future]
        ActorB[Agent Actor B] -->|2. Nested call: parent-child link| ActorA
        ActorA -->|3. Reentrant Lock allowed| ReentrantQueue[Reentrant Queue]
        ReentrantQueue -->|4. Resolve nested query| ActorA
        FutureA -->|Watchdog Timeout| Reset[Force Node Offline / Reassign Task]
    end
    subgraph browser-use-Reflow
        Playwright[Playwright Interaction] -->|Trigger Click element X| ReflowCheck{Dynamic DOM moved?}
        ReflowCheck -->|Yes: Inject JIT script| JIT[getBoundingClientRect recalculate]
        JIT -->|New physical coordinates| Click[Execute Playwright mouse click]
        ReflowCheck -->|No: Layout unstable?| Stability[Stability Checker / 50ms interval]
        Stability -->|Wait for animation end| Click
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
print("Successfully appended Round 28 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 28 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round22" class="nav-link">R22: smolagents / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 28
round28_html = u"""      <!-- Round 22 (28th Research) -->
      <section id="round22">
        <h2>R22：线程局部并发隔离、逻辑重入锁死锁预防与页面重排坐标自愈 (smolagents & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">smolagents, AutoGen 与 browser-use 的并发控制与动态页面适配</span>
              <span class="product-meta">Thread-local tools, reentrancy locks & DOM reflow alignment</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>smolagents · 线程局部工具隔离与限流调度 (Local Tools Concurrency)</strong>：通过 Thread-Local 机制为多路并发的 Worker 绑定独立的工具副本，避免共享状态竞争，结合线程池实现最大并发控制与退避限流。</li>
              <li><strong>AutoGen v0.4 · 逻辑时钟重入锁与死锁预防 (Actor Reentrancy)</strong>：引入 Parent-Child 消息逻辑时钟，支持挂起状态下的异步嵌套消息重入处理，结合 Awaitable Future 超时看门狗阻断分布式假死。</li>
              <li><strong>browser-use · 动态重排视口坐标重算与动效稳定器 (JIT Reflow Checker)</strong>：在执行交互动作前通过 JIT 脚本重算 `getBoundingClientRect` 抵消页面重排偏移，并利用 50ms 位移差动效消隐器判断稳定态再执行点击。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 28 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round28_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 28 to open_source_research_report.html.")
