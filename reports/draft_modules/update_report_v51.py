# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 51 Updater
Appends the 51th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第五十一分次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的多租户执行隔离与资源配额限速、AutoGen v0.4 的 Actor 动态上下文压缩与向量内存整合、browser-use 的有状态 Web 会话池与预提取上下文回收

#### 1. LlamaIndex Workflows (多租户执行隔离与资源配额限速)
*   **核心创新一：多租户沙箱协程上下文隔离 (Multi-Tenant Execution Isolation)**
    *   *机制原理*：在企业级多租户场景下，大量不同用户的 Workflow 同时运行在相同的物理执行池中，如果不进行物理/逻辑隔离，极易发生“脏数据跨租户读写”以及“抢占计算资源造成的邻居干扰（Noisy Neighbor）”。LlamaIndex Workflows 为每个 Tenant（租户）分配一个完全隔离的沙箱协程命名空间（Isolated Context namespace），使得租户内部的状态日志、运行中间变量在物理层面绝对无法互通。
*   **核心创新二：基于漏桶算法的资源配额动态限速 (Resource Quota Throttling)**
    *   *机制原理*：为了防止单个恶意租户通过生成海量并行事件瞬间占满系统线程池或消耗超出预算的 LLM Token，Workflows 在总线分发层部署了基于漏桶算法的“配额限速控制器”。控制器实时统计并平滑控制每个租户的并发协程数、每分钟 LLM 交互 Token 数量以及外部数据库并发连接数，超出配额的事件会被挂起缓冲，保障了全局多租户运行的高可用性。

#### 2. Microsoft AutoGen v0.4 (Actor 动态上下文压缩与向量内存整合)
*   **核心创新一：运行态 Actor 动态上下文有损/无损压缩 (Dynamic Context Compaction)**
    *   *机制原理*：在长周期的多智能体持续对话和交互中，聊天历史（Chat History）和执行轨迹（Trace Log）会随着时间推移呈线性增长，极易突破大模型的最大上下文窗口（Context Window），同时大幅提高每次请求的延迟与 Token 成本。AutoGen 0.4 的 Actor 运行时内置了动态上下文压缩引擎：当消息的 Token 总数超过设定阈值（例如 8k）时，系统自动在后台拉起专用的摘要生成链，将冗长的交互细节压缩为高密度的结构化事实陈述，透明地替换对话历史中的旧消息。
*   **核心创新二：混合式向量内存整合与事实检索 (Vector Memory Consolidation)**
    *   *机制原理*：被压缩掉的原始对话细节并不会被简单丢弃，而是通过语义切片（Semantic Chunking）转换为高维向量，异步持久化写入内置的向量内存数据库（Vector Memory）中。在后续交互中，Actor 会动态提取当前输入的 Query，在向量内存中进行快速检索（Cosine Similarity），并将召回的相关事实动态拼接到当前的上下文窗口中，实现了无限周期下低延迟、高召回的智能体记忆系统。

#### 3. browser-use (有状态 Web 会话池与预提取上下文回收)
*   **核心创新一：有状态浏览器会话池热备管理 (Stateful Web Session Pools)**
    *   *机制原理*：在并行自动测试中，频繁启动新的 Chromium 实例并重新执行繁琐的系统登录（特别是包含 MFA 验证码、图形验证码的登录）是系统耗时的核心痛点。browser-use 设计了有状态 Web 会话池。系统维护着一组处于“热备（Warm Standby）”状态的浏览器上下文（Browser Contexts），这些上下文已经完成了基础登录、核心 JS 包的预加载以及本地缓存的初始化。当新 Agent 发起测试任务时，可以直接分配热备 Session，实现秒级响应。
*   **核心创新二：清理沙箱隔离与上下文预提取回收 (Prefetched Context Sanitization & Recycling)**
    *   *机制原理*：在分配的 Agent 使用完毕后，会话池管理器并不会直接销毁该浏览器页面，而是对其执行一次“快速沙箱净化（Sanitization）”：利用 CDP 协议清除临时 DOM 改动、重置 session 状态、恢复至默认的空白/起始工作页面，但不清除底层已验证的 Cookie 与预加载资源，随后将其作为可用资源重新回收（Recycle）进池中，为下一个任务实现近乎零延迟的接力运行。

```mermaid
graph TD
    subgraph LlamaIndex-MultiTenant-Isolation
        EventA[Tenant A Event] -->|Isolated Context A| Engine[Workflows Dispatcher]
        EventB[Tenant B Event] -->|Isolated Context B| Engine
        Engine -->|Leaky Bucket Token Check| Quota[Resource Quota Throttling]
        Quota -->|Within Limit| ThreadA[Tenant A Coroutines]
        Quota -->|Exceeds Limit| Suspend[Buffer & Delay Event]
    end
    subgraph AutoGen-Memory-Consolidation
        Chat[Chat History > 8k Tokens] -->|1. Trigger Compaction| Summarizer[Background Fact Summarizer]
        Summarizer -->|2. Compressed facts replace old chat| ActiveContext[Active Chat Context]
        Chat -->|3. Async Vector Embedding| VectorDB[(Local Vector Memory DB)]
        NewQuery[New Agent Input] -->|4. Hybrid search| VectorDB
        VectorDB -->|5. Inject relevant historic facts| ActiveContext
    end
    subgraph browser-use-Session-Pool
        Request[Agent requests warm session] -->|1. Pop warm context| Pool[Stateful Browser Session Pool]
        Pool -->|2. High-speed ready state| Page[Active Browser Page]
        Page -->|3. Complete test action| Finish[Task Completed]
        Finish -->|4. Clean temp DOM & storage| Sanitizer[CDP Sanitizer]
        Sanitizer -->|5. Push sanitized context back| Pool
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
print("Successfully appended Round 51 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 51 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round45" class="nav-link">R45: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 51
round45_html = u"""      <!-- Round 45 (51th Research) -->
      <section id="round45">
        <h2>R45：多租户沙箱协程隔离配额限速、Actor 运行态上下文动态压缩与浏览器有状态热备会话池 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的隔离与缓存池机制</span>
              <span class="product-meta">Multi-tenant isolation, context compaction & stateful browser pools</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 多租户命名空间隔离与基于漏桶算法的资源配额限速 (Tenant Sandboxing)</strong>：确保多租户运行时并发控制与变量环境的强隔离，平滑超出配额的多并发事件。</li>
              <li><strong>AutoGen v0.4 · 消息Token超阈值上下文动态压缩与向量存储异步召回 (Context Compaction)</strong>：在运行时透明压缩庞大交互记录为关键事实摘要，并辅以向量检索机制在长周期内按需拼回上下文。</li>
              <li><strong>browser-use · 有状态浏览器会话池热备与CDP净化重置快速回收 (Session Context Pool)</strong>：缓存已登录并预加载的热备页面上下文供Agent极速接力，退出时通过CDP静默清除改动以实现零延迟再循环。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 51 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round45_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 51 to open_source_research_report.html.")
