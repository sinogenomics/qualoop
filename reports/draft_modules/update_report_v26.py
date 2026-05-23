# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 26 Updater
Appends the 26th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第二十六次调研（2026-05-23）: 深入分析 LlamaIndex Workflows 的多智能体全局上下文共享与语义检索记忆、AutoGen v0.4 的 Protobuf 强类型 Schema 序列化与代码生成、OpenHands 的基于 Pexpect 交互式 Shell 挂载与超时看门狗

#### 1. LlamaIndex Workflows (多智能体全局上下文共享与语义检索记忆)
*   **核心创新一：分层上下文状态共享 (Hierarchical Workflow Context Sharing)**
    *   *机制原理*：在复杂的多智能体系统中，各子 Agent 需要读取全局变量（如 North Star、配置信息）但同时需要维护局部私有的临时变量。LlamaIndex Workflows 提供了分层的 `Context` 状态管理。主 Workflow 维护全局共享的 Key-Value 字典，子 Agent 可以读写共享的上下文节点，同时其私有变量只存在于 `@step` 局部的局部变量中，防止了并发调用下的上下文竞态和命名冲突。
*   **核心创新二：事件驱动的动态语义记忆检索 (Event-Triggered Semantic Memory Retrieval)**
    *   *机制原理*：为了防止上下文窗口被历史日志和代码膨胀撑爆，Workflows 支持将全局上下文与向量数据库（Vector DB）进行深度集成。当触发特定事件（如 `ContextMissingEvent`）时，Workflow 会自动使用 Embedding 模型对当前步骤的错误或任务描述进行向量化，在本地内存向量数据库中检索最相似的 3 个历史成功修复案例并动态注入当前步骤，实现了按需的语义记忆检索。

#### 2. Microsoft AutoGen v0.4 (Protobuf 强类型 Schema 序列化与代码生成)
*   **核心创新一：基于 Protobuf 的多语言契约生成 (Protobuf-based Multi-language Contract Generation)**
    *   *机制原理*：跨语言（Python, TypeScript, Go 等）协作的智能体系统极易因为 JSON 格式变动或拼写错误导致运行时崩溃。AutoGen v0.4 将所有智能体之间的通信消息定义为标准的 `.proto` 格式（Protocol Buffers）。通过 `protoc` 编译器在编译期自动生成各个语言的强类型数据类与接口。这保证了哪怕一个 Go 编写的文件观察探针与 Python 编写的推理 Scorer 之间进行通信，两端的字段和类型注解也是完全对齐且静态可检查的。
*   **核心创新二：动态消息验证与反序列化边界保障 (Dynamic Message Serialization Validation)**
    *   *机制原理*：在大语言模型生成不符合规范的 Tool 响应时，系统必须能在接口层阻断错误。AutoGen 0.4 在 gRPC 接收端内置了强验证边界（Validation Barrier）。在接收到二进制 Protobuf 消息流后，首先通过字段校验器进行结构化检查，一旦发现缺失必须字段（如 `tool_call_id`），直接抛出明确的序列化异常并在网关层自动触发 Agent 的重试机制，避免脏数据污染 Agent 核心状态。

#### 3. OpenHands (基于 Pexpect 交互式 Shell 挂载与超时看门狗)
*   **核心创新一：基于 Pexpect 的伪终端交互挂载 (Pexpect-driven Pseudo-Terminal Interactive Shell)**
    *   *机制原理*：智能体运行测试或交互式命令（如需要输入 `[y/N]` 或交互式提示的 pip 安装）时，简单的 `subprocess.run` 会无限期阻塞。OpenHands 通过 `pexpect` 库在 Docker 内部挂载伪终端（Pty）。它能够在后台流式读取控制台输出，利用正则表达式匹配常见的交互式提示符（如 `password:`, `proceed [y/n]?`），并自动注入预设的输入，实现了真正意义上的交互式 Shell 执行。
*   **核心创新二：三级超时看门狗与异常输出熔断 (Three-Tier Timeout Watchdogs & Execution Circuit Breaker)**
    *   *机制原理*：在运行恶意或有缺陷的代码时，代码可能包含死循环或无限等待，耗尽 CPU 和时间。OpenHands 内置了三级超时看门狗机制：第一级为单条命令的最大执行时长（如 60s），第二级为单次 Task 累计执行时长（如 10m），第三级为 CPU/内存占用率阈值。当任意一级阈值被触发时，看门狗会立即发送 `SIGKILL` 强制终止 Docker 中的子进程，捕获异常栈并触发熔断，保障宿主机稳定。

```mermaid
graph TD
    subgraph LlamaIndex-Memory-Sharing
        WorkflowContext[(Global Workflow Context Store)] <-->|Read / Write| StepNode[Workflow Step Node]
        StepNode -->|ContextMissingEvent| Embedder[Text Embedding Service]
        Embedder -->|Query Vector| VectorDB[(Local Memory Vector DB)]
        VectorDB -->|Retrieve top 3 gold trajectories| StepNode
    end
    subgraph AutoGen-v04-Protobuf
        ProtoFile[Agent Messages Contract: msg.proto] -->|protoc compiler| PythonClass[Python Typed Messages]
        ProtoFile -->|protoc compiler| TSClass[TypeScript Typed Messages]
        PythonClass -->|1. Binary Serialization| gRPC[gRPC Communication Layer]
        gRPC -->|2. Receive & Check| Barrier[Validation Barrier / Check required fields]
        Barrier -->|Fail: Trigger retry| TSClass
    end
    subgraph OpenHands-Pexpect-Watchdog
        AgentCmd[Execute interactive command] -->|pseudo-terminal pty| Pty[Pexpect interactive loop]
        Pty -->|Regex match prompt| AutoInput[Auto inject user inputs: Y / password]
        Pty -->|Stream stdout| DockerVM[Docker Sandbox]
        Watchdog[Three-Tier Watchdog CPU/Mem/Time] -->|Monitor| DockerVM
        Watchdog -->|Timeout or CPU spike| Kill[SIGKILL process / Trigger Circuit Breaker]
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
print("Successfully appended Round 26 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 26 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round20" class="nav-link">R20: LlamaIndex / AutoGen / OpenHands</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 26
round26_html = u"""      <!-- Round 20 (26th Research) -->
      <section id="round20">
        <h2>R20：全局上下文共享与语义检索、Protobuf 消息契约与 Pexpect 交互式终端 (LlamaIndex & AutoGen & OpenHands)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">LlamaIndex, AutoGen 与 OpenHands 的记忆与交互通道设计</span>
              <span class="product-meta">Hierarchical Context memory, Protobuf serialization & Pty watchdogs</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>LlamaIndex Workflows · 全局分层上下文与动态语义检索 (Semantic Context)</strong>：提供分层 context 状态共享，并支持当发生异常或任务中断时，自动对错误信息进行向量化并在内存向量库中检索相似修复案例进行按需注入。</li>
              <li><strong>AutoGen v0.4 · Protobuf 强类型契约与动态反序列化验证 (Protobuf Validation)</strong>：基于 `.proto` 定义强类型多语言消息契约，并通过 gRPC 接收端的强校验边界（Validation Barrier）动态过滤非确定性 LLM 脏数据。</li>
              <li><strong>OpenHands · Pexpect 伪终端挂载与三级超时看门狗 (Pty & Watchdogs)</strong>：通过 `pexpect` 库在容器中建立 Pty 伪终端自动应答控制台提示，结合三级超时熔断看门狗强制 SIGKILL 死循环任务，防止宿主机资源耗尽。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 26 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round26_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 26 to open_source_research_report.html.")
