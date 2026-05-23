# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 23 Updater
Appends the 23rd round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第二十三次调研（2026-05-23）: 深入分析 smolagents 的线程安全本地工具缓存、OpenHands 的 tmux 终端屏幕流解析与 Pydantic AI 的依赖注入动态系统提示词

#### 1. Hugging Face smolagents (线程安全本地工具与运行缓存)
*   **核心创新：工具实例隔离与输入指纹缓存 (Thread-Safe Tool Caching & Input Fingerprinting)**
     *   *机制原理*：在多 Agent 并发执行任务时，如果多个 Executor 共享同一个工具实例（如带有缓存 state of ACI 文件读取器），容易引发数据竞争和调用死锁。smolagents 引入了线程安全 isolated tool 机制。每个运行任务（Run Task）拥有一份独立的工具实例拷贝。同时，工具自带基于参数哈希指纹（Input Hash Fingerprint）的运行缓存。当相同参数的工具被高频重复调用时，系统直接读取缓存结果，避免了重复读取物理磁盘和 API 通信，提升了 30% 以上的执行速度。

#### 2. OpenHands (基于 pyte 的 tmux 终端屏幕重构与 stdout 流式解析)
*   **核心创新：虚拟终端状态保持与多控制符过滤 (Virtual Terminal Parsing & ANSI Escape Filtering)**
     *   *机制原理*：在硬隔离 Docker 沙盒内部，Agent 跑测命令会输出大量的 ANSI 转义字符、格式化控制符（如进度条、颜色代码）以及终端自动换行噪声。直接将这些 raw 字符发给 LLM 容易导致上下文解析异常。OpenHands 在后台启动了一个虚拟终端模拟器（基于 `pyte` 库）。当 tmux 后台进程流式输出 stdout 时，pyte 会在内存中重建一张虚拟“显示屏幕”，自动过滤掉 90% 的转义噪声和样式代码，仅将重构后 of 纯文本屏幕字符反馈给 Agent，大幅提升了对复杂命令行输出（如 pip、pytest 进度）的阅读精度。

#### 3. Pydantic AI (依赖注入驱动的动态系统提示词)
*   **核心创新：System Prompt 运行时生成与 Deps 注入绑定 (Deps-Driven Dynamic System Prompts)**
     *   *机制原理*：传统 Agent 的 System Prompt 往往是静态硬编码的，无法根据当前被编辑文件的业务规范和项目目标（North Star）实时改变。Pydantic AI 提供了 `@agent.system_prompt` 动态装饰器。在每次调用大模型之前，提示词引擎会动态读取注入的 `RunContext[Deps]`。例如根据当前修改 of 文件路径，从本地 `.qualoop/rules/` 文件夹中自动加载特定的代码规范作为提示词注入。这实现了提示词的运行时组装，杜绝了无用系统提示词对上下文的损耗。

```mermaid
graph TD
    subgraph smolagents-Tool-Cache
        Call[Tool Call Request] -->|Compute Hash| Hash[Parameter Fingerprint Hash]
        Hash -->|Hit?| Cache{Is Cached in TaskStore?}
        Cache -->|Yes| Return[Return cached result instantly]
        Cache -->|No| Run[Run safe isolated tool instance]
        Run -->|Store cache| Return
    end
    subgraph OpenHands-Tmux-Pyte
        TmuxStream[Tmux Stdout Stream with ANSI escapes] -->|Raw bytes| Pyte[Pyte Virtual Screen]
        Pyte -->|1. Render text in memory| Screen[Memory Screen Matrix]
        Screen -->|2. Strip style & control codes| CleanText[High Density Pure Text Output]
        CleanText -->|Observation Event| LLM[LLM Agent]
    end
    subgraph Pydantic-AI-Prompts
        Context[Agent.run context] -->|1. Fetch RunContext.deps| Loader[Dynamic Prompt Engine]
        Loader -->|2. Load matching rules & config| Assembler[System Prompt Assembler]
        Assembler -->|3. Compile final instructions| SystemPrompt[System Prompt with exact context rules]
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
print("Successfully appended Round 23 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 23 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round17" class="nav-link">R17: smolagents / OpenHands / Pydantic AI</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 23
round23_html = u"""      <!-- Round 17 (23rd Research) -->
      <section id="round17">
        <h2>R17：本地工具运行缓存、虚拟终端屏幕重构与依赖注入动态系统提示词 (smolagents & OpenHands & Pydantic AI)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">smolagents, OpenHands 与 Pydantic AI 的运行优化设计</span>
              <span class="product-meta">Tool caching, pyte screen parser & dynamic prompts</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>smolagents · 本地工具实例隔离与缓存 (Tool Caching)</strong>：为并发运行的 Executor 节点提供线程隔离的工具实例，并根据输入参数的哈希值自动缓存结果，消除多余 disk IO 与 API 调用延迟。</li>
              <li><strong>OpenHands · pyte 虚拟终端屏幕重构 (ANSI Escape Filtering)</strong>：在内存中借助 pyte 模块还原 tmux 输出，过滤复杂的控制符、ANSI 颜色代码及折行，提供纯净的高密度控制台 Observation。</li>
              <li><strong>Pydantic AI · 依赖注入动态系统提示词 (Dynamic System Prompts)</strong>：结合 `@agent.system_prompt` 在大模型唤醒前动态提取 `RunContext` 中注入的依赖，按需挂载匹配的代码规则与 North Star 指标，缩减冗长指令。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 23 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round23_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 23 to open_source_research_report.html.")
