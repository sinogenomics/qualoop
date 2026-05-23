# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 16 Updater
Appends the 16th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第十六次调研（2026-05-23）: 深入分析 Devin/OpenHands 运行态工作区环境快照恢复、Mentat 的语义上下文文件钉选与 CrewAI 的跨角色多维向量记忆同步

#### 1. Devin/OpenHands (物理工作区运行态快照与进程挂起恢复)
*   **核心创新：Docker 卷差异快照与活动进程快照挂起 (Sub-second Docker Volumed Checkpointing & Process Suspend)**
     *   *机制原理*：在长周期的自动修复流程中，一旦测试或编译失败，仅仅回退 git 文件修改是不够的。许多运行时错误是由于测试数据库被写脏、临时生成 of 缓存文件冲突或后台服务卡死导致的。Devin 和 OpenHands 在微步执行前后，不仅对 git 树做 commit，而且利用 Docker Volume Diff 记录工作区目录 changes。同时，通过向进程发送 `SIGTSTP` 或对关键运行进程进行快照挂起（Checkpoint/Restore In Userspace，CRIU），可在发生故障时，在亚秒级内把包括进程状态和内存、缓存及数据库数据一并还原到上一个健康检查点。

#### 2. Mentat (语义上下文文件钉选与动态 Token 降噪预算)
*   **核心创新：高相关性上下文锁定与滑动窗口预算控制 (Context File Pinning & Slidewindow Token Budgeting)**
     *   *机制原理*：大模型上下文非常宝贵，Agent 在修改跨模块 Bug 时极易产生冗余的 context 占用。Mentat 支持动态 File Pinning（钉选）机制，自动将高置信度的文件作为核心上下文锁死。而其他临时读取/查找的文件，则遵循滑动窗口淘汰机制（FIFO）。一旦即将超出模型最舒适的 Token 区间，系统会主动对未钉选文件进行内容压缩（如仅保留类和函数的头部签名），既不丢失结构化视野，又防止了上下文过长导致的注意力分散和高昂费用。

#### 3. CrewAI (跨角色多维向量记忆同步)
*   **核心创新：多智能体联合向量存储同步与交叉认知共享 (Cross-Agent Centralized Embeddings Sync)**
     *   *机制原理*：在多 Agent 协同流程（如 Product Manager Agent 产出 PRD，QA Agent 进行测试用例设计）中，传统的做法是编写冗长 of 提示词进行人工数据传递。CrewAI 为多智能体配备了统一的数据总线。每个 Agent 在执行 Task 后，其产生的 stdout 报告和变更结论都会自动被转换为 Vector Embeddings，同步发布到全局 Central RAG Database 中。当其他角色（如 QA）被唤醒时，系统自动进行语义匹配召回，使各 Agent 能在“不显式进行系统 Prompt 级数据传递”的情况下，天然共享最新的项目事实，实现高度同步的交叉认知。

```mermaid
graph TD
    subgraph Devin-Workspace-Snapshots
        Run[Agent Action] -->|Create Checkpoint| DockerDiff[Docker Volume Diff + CRIU Process Dump]
        DockerDiff -->|1. Revert files| OriginalFS[还原物理文件系统]
        DockerDiff -->|2. Restore memory state| MemoryRestored[还原挂起服务与进程状态]
    end
    subgraph Mentat-Pinning
        ContextWindow[大模型上下文窗口] -->|Pin| CoreFiles[核心锁定文件: 全量注入]
        ContextWindow -->|FIFO Slide Window| TempFiles[临时访问文件]
        TempFiles -->|Token limit exceeded| TokenCompressor[自动符号头压缩]
    end
    subgraph CrewAI-VectorSync
        PM[PM Agent] -->|Generates spec| Embedder[Vector Embedder]
        Embedder -->|Publish| VectorStore[(共享向量数据库)]
        VectorStore -->|Semantic retrieval| QA[QA Agent / Code Generator]
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
print("Successfully appended Round 16 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 16 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round10" class="nav-link">R10: Devin / Mentat / CrewAI</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 16
round16_html = u"""      <!-- Round 10 (16th Research) -->
      <section id="round10">
        <h2>R10：运行态环境快照恢复、滑动窗口 Token 降噪钉选与跨智能体向量内存共享 (Devin & Mentat & CrewAI)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">Devin/OpenHands, Mentat 与 CrewAI 的高级协作特性</span>
              <span class="product-meta">CRIU Docker Snapshot, FIFO Slide Pinning & Cross-Agent Vector Store</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>Devin/OpenHands · Docker卷与进程级快照 (Workspace State Checkpointing)</strong>：结合 Docker Volume Diff 和 CRIU (Userspace Checkpoint/Restore) 进程转储技术，实现对文件系统、数据库状态及后台卡死服务的秒级状态还原，大幅超越传统的纯 git rollbacks。</li>
              <li><strong>Mentat · 钉选与滑动窗口 Token 压缩 (Slide Window Pinning)</strong>：钉选核心文件进行全量上下文传递，其他临时访问文件在接近 Token limit 时自动通过 AST 降级为仅保留头部签名，最大化注意力和经费利用率。</li>
              <li><strong>CrewAI · 跨角色多维向量记忆同步 (Cross-Agent Shared Vector)</strong>：各智能体将步骤结论与日志转换成 Embeddings 同步发布到共享的 RAG 向量数据库，从而让被动唤醒的下游智能体能通过语义自动检索，无需显式在 System Prompt 里传递数据。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 16 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round16_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 16 to open_source_research_report.html.")
