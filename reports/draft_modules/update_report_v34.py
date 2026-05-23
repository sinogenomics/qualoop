# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 34 Updater
Appends the 34th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第三十四次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的嵌套子工作流强类型结构化数据传递、AutoGen v0.4 的 Actor 邮箱滑动窗口 LLM 限速与退避与 browser-use 的 CDP 原生网络请求拦截与敏感载荷审计

#### 1. LlamaIndex Workflows (嵌套子工作流强类型结构化数据传递)
*   **核心创新一：嵌套子工作流的契约化输入输出 (Contracted Input/Output for Sub-Workflows)**
    *   *机制原理*：在长周期的多智能体协调中，嵌套子图如果只通过松散的字典传递参数，极易因参数命名或类型变动导致运行时崩溃。LlamaIndex Workflows 支持为嵌套的子图声明严格的输入事件（`InputEvent`）与输出事件（`OutputEvent`）契约。父图在触发子工作流时，必须构建包含强类型校验字段的事件实例，子图在计算完成后也会生成带有 Pydantic 校验的输出事件传递回父图上下文，保障了模块间通信的强一致性。
*   **核心创新二：父子上下文的数据双向同步与快照继承 (Context Synchronization and Snapshot Inheritance)**
    *   *机制原理*：子图虽然运行在隔离的事件循环内，但在执行缺陷定位时，通常需要继承父图已加载的代码树指针和配置凭证。Workflows 支持父子上下文的高性能同步。子图启动时会自动克隆（Clone）父图的快照数据区，而在子图生命周期结束后，其修改的全局状态（如更新的 Issues store）会自动回写合并（Merge）到父图的上下文，避免了数据孤岛的产生。

#### 2. Microsoft AutoGen v0.4 (Actor 邮箱滑动窗口 LLM 限速与退避)
*   **核心创新一：带有 HTTP 429 感知的滑动窗口限流器 (Rate-limit Aware Sliding Window Throttler)**
    *   *机制原理*：多智能体并发调用在线大模型 API（如 OpenAI, Anthropic）时，极易因瞬时并发量过大触发限额（Rate Limits）引发服务中断。AutoGen v0.4 在 Actor 邮箱通道上集成了滑动窗口限流器。当网关检测到 HTTP 429 或限频警告时，限流器会自动调整发送窗口大小，将邮箱队列中的出站请求进行延时缓冲，避免触发严重的物理封禁，保障了长周期多 Agent 并行执行的连续性。
*   **核心创新二：指数退避与分布式并发抖动 (Exponential Backoff with Concurrency Jitter)**
    *   *机制原理*：当多个 Agent 节点同时被限速并开始重试时，如果重试间隔完全一致，会产生“惊群效应（Thundering Herd）”，导致 API 提供商发生二次限速。AutoGen 邮箱系统内置了抖动退避机制。每个 Actor 的重试间隔（Interval）会乘以一个随机的抖动因子（Jitter）。这种时间维度上的随机离散化有效消除了重试流量的洪峰，提高了 API 在高吞吐修复任务下的调用成功率。

#### 3. browser-use (CDP 原生网络请求拦截与敏感载荷审计)
*   **核心创新一：Chrome DevTools Protocol (CDP) 异步请求劫持 (CDP Network Request Hijacking)**
    *   *机制原理*：在自动 Tester 跑测 Web 页面时，部分敏感信息（如 API 密钥泄露、未授权的网络越权外泄）不会直接呈呈现 DOM 树上，因此常规的视觉或 DOM 审计无法察觉。browser-use 通过 Playwright 的底层 CDP（Chrome DevTools Protocol）连接，直接拦截浏览器出站与入站的所有网络请求包。它可以在不修改页面 JS 的前提下，流式捕获原始 HTTP 请求头（Headers）与数据体（Payloads），为安全分析提供最底层的数据流。
*   **核心创新二：运行时请求载荷安全规则审查 (Real-Time Payload Rule Audit)**
    *   *机制原理*：获取到网络数据包后，browser-use 引擎会将 Payload 自动输入拦截扫描插件。扫描器使用高效的正规表达式或签名指纹，对数据包内容进行实时审查，一旦检测到包含敏感秘钥格式、未脱敏的用户数据库记录、或发往未授权域名的数据外泄，会立即在拦截层抛出 `SecurityAuditViolation` 异常并挂起标签页，实现了网络物理层的安全围栏。

```mermaid
graph TD
    subgraph LlamaIndex-Context-Sync
        ParentContext[(Parent Context Database)] -->|1. Clone Snapshot| ChildContext[(Child Context Sandbox)]
        ChildContext -->|2. Run isolated Sub-Workflow| SubRunner[Sub-Workflow Runner]
        SubRunner -->|3. Output strong-typed Event| Bubble[Bubbled Event / Return Contract]
        Bubble -->|4. Merge modifications| ParentContext
    end
    subgraph AutoGen-v04-Throttler
        ActorMailbox[Actor Outbound Mailbox] -->|1. Detect HTTP 429| Throttler[Sliding Window Throttler]
        Throttler -->|2. Shrink window size| Buffer[Delayed Outbox Buffer]
        Buffer -->|3. Retry with Exponential Backoff + Jitter| LLMAPI[LLM API Endpoints]
    end
    subgraph browser-use-CDP-Audit
        Playwright[Playwright Browser Session] -->|CDP Connection| CDP[Chrome DevTools Protocol]
        CDP -->|1. Intercept Outbound payload| RawPackets[Raw Request Headers & Payloads]
        RawPackets -->|2. Regex / Signature audit| Rules{Leaked key / unauthorized domain?}
        Rules -->|Yes: Block & Raise| SecurityAuditViolation[SecurityAuditViolation / Suspend Tab]
        Rules -->|No| Send[Allow Network Send]
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
print("Successfully appended Round 34 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 34 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round28" class="nav-link">R28: LlamaIndex / AutoGen / browser-use</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 34
round34_html = u"""      <!-- Round 28 (34th Research) -->
      <section id="round28">
        <h2>R28：子工作流契约化数据同步、邮箱 API 限频退避与 CDP 原生网络拦截审计 (LlamaIndex & AutoGen & browser-use)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 browser-use 的契约通信与限流审计机制</span>
              <span class="product-meta">Contracted sub-context, sliding throttler & CDP payload audit</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 子工作流契约化输入输出与快照双向同步 (Contracted Sync)</strong>：通过强类型 Input/Output 规范嵌套子图通信契约，子图启动时克隆父图数据，结束后自动双向写回合并，避免数据孤岛。</li>
              <li><strong>AutoGen v0.4 · 滑动窗口 API 限流器与并发退避抖动 (Rate-limit Jitter)</strong>：集成 429 报错感知的滑动窗口出站缓冲器，结合指数退避和随机并发抖动消除 Thundering Herd 效应，保障高频调用强壮度。</li>
              <li><strong>browser-use · CDP 协议原生网络流量拦截与敏感 Payload 扫描 (CDP Network Audit)</strong>：利用 Playwright 的 CDP 接口劫持未在 DOM 渲染 of 底层网络报文，实时正则检索密钥泄露及未授权外传，构建网络物理层安全围栏。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 34 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round34_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 34 to open_source_research_report.html.")
