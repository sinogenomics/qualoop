# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 15 Updater
Appends the 15th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第十五次调研（2026-05-23）: 深入分析 Aider 的动态查询仓库地图伸缩、SWE-agent 的语义轨迹少样本选择与 OpenHands 的持久沙盒 tmux 会话管理器

#### 1. Aider (超大规模仓库地图伸缩机制)
*   **核心创新：动态子映射与局部 PageRank 计算 (Dynamic Sub-mapping & Localized PageRank)**
     *   *机制原理*：在面对包含上万文件的超大型物理仓库时，静态的前 1024 Token 仓库地图会由于依赖树过于庞杂而导致关键符号信息被稀释。Aider 引入了动态局部子映射机制。系统在运行过程中，根据 Agent 当前编辑的目标文件及其关联 of 局部调用链（Caller/Callee），动态缩小 Tree-sitter PageRank 计算的子图范围。通过局部计算生成针对当前任务的高精地图，实现按需伸缩，避免长上下文干扰。

#### 2. SWE-agent (语义轨迹少样本选择)
*   **核心创新：金牌轨迹向量检索与动态 Few-Shot 注入 (Gold Trajectory Retrieval & Dynamic Few-shot Injection)**
     *   *机制原理*：为了引导 Agent 在面对全新工程库时采用正确的编辑策略，SWE-agent 引入了历史成功轨迹（Gold Trajectories）的语义检索机制。在 Agent 初始化阶段，系统将当前 Issue 描述进行向量编码，在预先校验通过的高分/满分修复事件库（Trajectory Vector DB）中进行相似度检索，选取最贴近当前缺陷类型的 2-3 个“完整编辑与测试动作链”作为 Few-shot 注入 Prompt。这种以史为镜的机制可防止 Agent 在不熟悉的库中误用危险命令或偏离 North Star。

#### 3. OpenHands (持久沙盒 tmux 会话管理器)
*   **核心创新：多进程持久 tmux 状态维持与流式 stdout 捕获 (Tmux-backed Persistent Sandbox Sessions)**
     *   *机制原理*：在沙盒化运行中，如果每次执行命令都是拉起全新的单次 Subprocess，则无法维持进程间的状态（如激活的 Python 虚拟环境、配置的临时环境变量或在后台挂载的测试服务器）。OpenHands 在 Docker 容器内部通过 `tmux` 维持一个或多个常驻的 Shell 会话。Agent 发送的所有 ACI 动作都会直接被输入到该 `tmux` 实例中，并且系统通过流式读取 `tmux` 的屏幕缓冲区捕获完整的实时输出，使得多次步骤间的环境变量和运行态天然保持一致。

```mermaid
graph TD
    subgraph Aider-RepoMap-Scaling
        FullGraph[全库符号依赖图] -->|1. Locate target files| LocalSubGraph[提取目标文件依赖子图]
        LocalSubGraph -->|2. Compute Local PageRank| MinMap[动态 1K Token 子地图]
    end
    subgraph SWE-agent-FewShot
        NewIssue[新问题 Issue] -->|向量检索| TrajDB[(高分成功轨迹库)]
        TrajDB -->|匹配 Top K 相似轨迹| FewShot[动态 Few-shot Prompt]
        FewShot -->|注入上下文| AgentRunner[Agent 运行器]
    end
    subgraph OpenHands-Tmux
        AgentCore[Agent 控制核心] -->|WebSocket Command| DockerDaemon[Docker Container]
        DockerDaemon -->|Run input| Tmux[Tmux Shell Session]
        Tmux -->|Stdout/Stderr buffer| ScreenCapture[屏幕流式捕获器]
        ScreenCapture -->|Observation Event| AgentCore
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
print("Successfully appended Round 15 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 15 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round9" class="nav-link">R9: Aider / SWE-agent / OpenHands</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 15
round15_html = u"""      <!-- Round 9 (15th Research) -->
      <section id="round9">
        <h2>R9：仓库地图伸缩、少样本语义轨迹与持久 sandboxed tmux 会话 (Aider & SWE-agent & OpenHands)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">Aider、SWE-agent 与 OpenHands 的前沿特性</span>
              <span class="product-meta">Dynamic Repo-map, Gold Trajectory & Tmux Sandbox</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>Aider · 动态子地图伸缩 (Dynamic Repo-map scaling)</strong>：针对万级超大代码库进行局部依赖 PageRank 重算，生成仅千级 token 大小的相关依赖小地图，降低大模型在分析全局依赖关系时的噪声干扰。</li>
              <li><strong>SWE-agent · 动态 Few-Shot 轨迹检索 (Trajectory Selection)</strong>：在问题启动时，将 Issue 描述编码成向量，自动在历史黄金/满分成功修复轨迹库中进行余弦相似度检索，召回相似案例作为 Few-shot prompt，引导 Agent 采取更安全的修复路径。</li>
              <li><strong>OpenHands · 持久 tmux 沙盒会话 (Persistent sandboxed tmux)</strong>：容器环境内部不采用单次 subprocess 运行，而是通过 tmux 后台会话实现多次动作之间的 Python 虚拟环境与环境变量的状态自然持久化。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 15 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round15_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 15 to open_source_research_report.html.")
