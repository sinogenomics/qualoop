# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 21 Updater
Appends the 21st round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第二十一次调研（2026-05-23）: 深入分析 OpenAI Swarm 的无状态 Handoff 路由流、Pydantic AI 的结构化校验错误反馈环与 E2B 的沙盒高层文件系统 API

#### 1. OpenAI Swarm (无状态 Handoff 路由流设计)
*   **核心创新：Tool-based Agent Transfer 与无状态控制循环 (Stateless Handoff Routing)**
     *   *机制原理*：传统多智能体设计（如 LangGraph）依赖厚重的全局状态图和外部 Checkpoint 数据库进行节点转移。Swarm 提出了极致去中心化的“无状态 Handoff”设计。每一个 Agent 本质上只是一组 Instructions 和 Tools（Python 函数）的组合。Agent 如果需要进行控制权交接，只需在 Tool 函数中直接返回另一个 `Agent` 实例。Swarm 的轻量级 Runner 在检测到返回值为 Agent 对象时，自动在内存中切换当前会话上下文的 System Prompt 目标，实现极致灵巧、低延迟的角色状态流转。

#### 2. Pydantic AI (强 Schema 运行时校验错误反馈循环)
*   **核心创新：JSON 校验异常自动归纳与模型自愈输入 (Structured Validation Error Loops)**
     *   *机制原理*：智能体系统在输出结构化数据（如 Scorer 导出的打分结构、Executor 生成的代码 metadata）时，若模型直接生成了破损字段或类型错误的 JSON，会引发后端崩溃。Pydantic AI 结合 Pydantic v2 构建了闭环自愈网关。在检测到 `ValidationError` 后，框架会自动拦截异常，利用 Pydantic 内置的结构化报错解析器，提炼出清晰的字段路径和期望类型说明，作为 Observation 实时追加到对话流中并二次调起大模型，实现零外部干预的类型字段自愈。

#### 3. E2B Sandboxes (基于高层 ACI 的沙盒文件系统 API)
*   **核心创新：抽象文件系统读写 API 与进程交互控制 (High-level Virtual Disk API)**
     *   *机制原理*：传统 ACI 执行器常使用 Bash 命令（如 `cat << 'EOF' > file.py`）往沙盒写入文件，这极易因为包含反引号、括号或 Unicode 特殊符号引发 Shell 解析报错。E2B 沙盒抛弃了低效的 Shell 级物理命令包装，在 microVM 宿主通信通道上封装了高层的 Filesystem API。Agent 通过直接调用 API（如 `sandbox.filesystem.write(path, content)`) 读写磁盘。底层的 gRPC 传输保证了数据的字节完备性，彻底规避了操作系统命令转义引起的格式腐化风险。

```mermaid
graph TD
    subgraph Swarm-Stateless-Handoff
        Runner[Swarm Client Run] -->|1. Run active agent| A1[Tester Agent]
        A1 -->|2. Call transfer_to_scorer tool| Tool[Tool returns ScorerAgent]
        Tool -->|3. Intercept & Switch prompt| Runner
        Runner -->|4. Run active agent| A2[Scorer Agent]
    end
    subgraph Pydantic-AI-Feedback
        LLM[LLM JSON Generator] -->|Invalid schema payload| Parser[Pydantic Validator]
        Parser -->|ValidationError Exception| Formatter[Error Parser & path extractor]
        Formatter -->|Observation: Path 'id' must start with QL-| LLM
    end
    subgraph E2B-Filesystem-API
        Agent[Qualoop Executor] -->|sandbox.filesystem.write| SDK[E2B Python SDK]
        SDK -->|Binary stream over KVM| VM[Firecracker MicroVM Sandbox]
        VM -->|Direct virtual disk write| Disk[Sandbox Filesystem]
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
print("Successfully appended Round 21 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 21 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round15" class="nav-link">R15: Swarm / Pydantic AI / E2B SDK</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 21
round21_html = u"""      <!-- Round 15 (21st Research) -->
      <section id="round15">
        <h2>R15：无状态 Handoff 路由流、Pydantic AI 校验自愈环与 E2B SDK 沙盒文件读写规范 (OpenAI Swarm & Pydantic AI & E2B SDK)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">Swarm, Pydantic AI 与 E2B SDK 的开发契约设计</span>
              <span class="product-meta">Stateless Handoff, validation loops & virtual disk access</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>OpenAI Swarm · 无状态 Handoff 路由 (Stateless Agent Transfer)</strong>：利用 Tool 直接返回下一个 Agent 实例，实现去中心化的轻量控制路由切换，极大简化多智能体并发拓扑流转。</li>
              <li><strong>Pydantic AI · 强校验异常自愈循环 (Validation feedback loops)</strong>：捕获强类型 Pydantic 错误异常并自动归纳出不合规字段与期望格式，反哺给 LLM 作为 Observation 实现快速自愈。</li>
              <li><strong>E2B SDK · 沙盒高层文件系统 API (Virtual Filesystem API)</strong>：不通过脆弱的 Bash 字符串包装写入磁盘，利用基于 gRPC 的 Filesystem API 直接对隔离 VM 执行读写，彻底规避操作系统转义兼容风险。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 21 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round21_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 21 to open_source_research_report.html.")
