# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 19 Updater
Appends the 19th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第十九次调研（2026-05-23）: 深入分析 Dify 的可视化 DAG 混杂执行工作流、Vercel AI SDK 的 Zod 原生结构化输出与 LangSmith 的嵌套 Run-Tree 离线回归测试

#### 1. Dify (可视化 DAG 混合流与 BaaS 数据集生命周期管理)
*   **核心创新：混合执行工作流引擎与可视化热插拔组件 (Visual Workflow Engine & BaaS Integration)**
     *   *机制原理*：传统 Agent 开发的拓扑关系极度抽象。Dify 引入了图形化 DAG 流程编排系统，将大模型节点、代码块（Code）、API 节点以及人工确认（HITL）以可视化连线连接，编译为强类型 JSON 树执行。同时，它将切片（Chunking）、Embedding 向量化以及外部 Vector Store 统一打包为后端即服务（BaaS），允许动态挂载不同 dataset 供 Tester 和 Scorer 进行语义搜索，极大降低了系统搭建的碎片化。

#### 2. Vercel AI SDK (Zod 驱动的原生结构化校验与流式渲染)
*   **核心创新：Zod 强类型 Schema 对准与流式 Object 渐进式渲染 (Zod Schema Validation & Progressive UI Streams)**
     *   *机制原理*：传统 Agent 接口在提取大模型生成的复杂 JSON 时十分脆弱。Vercel AI SDK 将 Zod Schema 与主流大模型的底层 JSON 模式和工具调用进行原生对准。一旦 LLM 生成的 JSON 不符合 Zod 类型约束，SDK 会在后台自动回喂详细 Schema 错误促使其自愈重试。此外，它提供了强大的流式 Object 响应接口（`streamObject`），使得大模型在持续写码或生成报告的过程中，前端 UI 能够以高刷新率实时显示可运行的结构化局部卡片，避免长等待。

#### 3. LangSmith (嵌套层级 Run-Tree 链路追踪与离线数据集回归)
*   **核心创新：无侵入式多级跟踪树与轨迹数据集评测 (Run-Tree Hierarchy & Offline Dataset Evaluations)**
     *   *机制原理*：随着智能体调用嵌套层次加深（如 Orchestrator 唤起 Executor，Executor 循环调用 ACI 并在沙盒跑测），传统的单层 log 会变得混乱不堪。LangSmith 建立了树状嵌套 Trace 体系，记录每一个子步骤的 Tokens 耗用和延迟。更核心的是，它支持将运行失败的 Agent 交互轨迹直接一键导出为“测试集（Dataset）”，并在后台批量跑 LLM-as-a-judge 或回归评测（Fail-to-pass / Pass-to-pass），彻底解决了代码升级导致的历史修复功能退化的痛点。

```mermaid
graph TD
    subgraph Dify-Visual-Workflow
        YAML[YAML / JSON Flow Tree] -->|1. Compile| Engine[Visual Node Orchestrator]
        Engine -->|LLM Node| LLM[LLM Call]
        Engine -->|BaaS Dataset| RAG[Vector Search / Chroma]
        Engine -->|HITL Node| HITL[人类审批闸门]
    end
    subgraph Vercel-AI-Zod
        Zod[Zod Schema Definition] -->|generateObject| LLMApi[Model Provider API]
        LLMApi -->|Raw Output| Check{Passes Zod validation?}
        Check -->|Yes| Client[Live Stream UI Form]
        Check -->|No: Auto-correct| LLMApi
    end
    subgraph LangSmith-RunTree
        TraceTree[Nested Run-Tree: Parent Span] -->|Child Span 1| Exec[Executor Action]
        TraceTree -->|Child Span 2| Sandbox[Sandbox run_test]
        TraceTree -->|Export Failure| Dataset[(Trace Dataset)]
        Dataset -->|Run Regression| Judge[LLM-as-a-judge Test Suite]
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
print("Successfully appended Round 19 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 19 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round13" class="nav-link">R13: Dify / Zod / LangSmith</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 19
round19_html = u"""      <!-- Round 13 (19th Research) -->
      <section id="round13">
        <h2>R13：可视化工作流混合执行、Zod 原生响应校验与嵌套 Run-Tree 离线回归测试 (Dify & Vercel AI SDK & LangSmith)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">Dify, Vercel AI SDK 与 LangSmith 的工程化特性</span>
              <span class="product-meta">Visual DAG, Zod validation & Run-Tree evaluation</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>Dify · 可视化 DAG 混合工作流 (Visual Workflow Flow)</strong>：将大模型、代码、外部 API 和人工网关统一用可视化流程连线编排并翻译为 JSON 执行，提供 BaaS 级统一数据集治理。</li>
              <li><strong>Vercel AI SDK · Zod 原生校验与流式 UI (Zod streamText)</strong>：将 Zod 模型校验强对准底层 JSON 模式和工具调用，自动捕获不匹配错误进行 LLM 后置修正，并支持边缘级流式状态渐进式同步。</li>
              <li><strong>LangSmith · 嵌套层级 Run-Tree 离线回归 (Nested Trace evaluation)</strong>：以有向层级树记录嵌套 Agent 动作、Tokens 耗用和时延，支持将失败轨迹一键生成离线评测数据集，进行 LLM-as-a-judge 批处理回归验证。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 19 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round19_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 19 to open_source_research_report.html.")
