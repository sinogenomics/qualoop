# -*- coding: utf-8 -*-
"""
Qualoop Open-Source Research Round 20 Updater
Appends the 20th round of deep research findings to reports/open_source_research.md
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

timeline_insert = u"""### 📅 第二十次调研（2026-05-23）: 深入分析 smolagents 的代码型工具调用安全解释器、Semantic Kernel 的原生函数绑定序列化与 OpenHands 的命令安全扫描插件

#### 1. Hugging Face smolagents (代码工具调用与本地内存解释器沙箱)
*   **核心创新：AST 安全沙箱代码解析与资源界限控制 (In-Memory Safe AST Evaluation)**
     *   *机制原理*：为了规避重量级 Docker 带来的冷启动时延，smolagents 探索了极速的“内存解释沙盒”。系统自定义了 PythonInterpreter，通过 AST 树深度优先遍历自主还原 Python 代码逻辑。它彻底剥离了 `eval` 和 `exec` 等高危内建函数，并严格限制导入模块与全局作用域。同时，为运行环境设置了精准的 CPU 运行时间（Execution Timeout）与内存分配上限，将恶意提权和 CPU 暴击直接消灭在内存解析阶段。

#### 2. Microsoft Semantic Kernel (原生函数绑定序列化与类型映射适配器)
*   **核心创新：参数 Schema 自动映射与复合类型序列化 (Type Mapping Adapters & Schema Bindings)**
     *   *机制原理*：传统 JSON 传参不支持复杂的类对象和嵌套实体。Semantic Kernel 提供了强类型的原生函数绑定适配器（Native Function Binding Adapters）。它能够自动解析 C# Class / Python dataclass 的底层属性，自动编译出嵌套 of JSON Schema 发送给 LLM。在大模型返回参数后，适配器在底层完成 JSON 到原生实例的反序列化转换，确保了复杂类型在工具传递链中的鲁棒性。

#### 3. OpenHands (命令安全扫描拦截插件)
*   **核心创新：正则阻断拦截器与安全漏洞主动建账 (Pattern-matching Security Guardrails)**
     *   *机制原理*：在 L3 级别的 Executor 运行自动命令行时，大模型极易受到恶意的 Prompt 注入进而执行高危命令。OpenHands 引入了 `Security Guardrail` 拦截插件。它在指令下发至 Docker tmux 之前，使用静态安全模式匹配对命令行进行静态审查，阻断类似越权读取环境变量（如 `env`, `printenv`）及高危物理删除（如 `rm -rf /`）命令，并自动在 Issue Store 中建立 `security_alert` 类型的缺陷，挂起流程，确保生产库绝对安全。

```mermaid
graph TD
    subgraph smolagents-AST-Sandbox
        Code[Agent Python Code] -->|AST Parse| AST[AST Node Visitor]
        AST -->|Check WhiteList| Eval[In-Memory Logic Evaluator]
        Eval -->|Timeout & Memory check| SafeReturn[Return variable state]
    end
    subgraph SK-Type-Adapters
        Func[Native python function] -->|1. Inspect dataclass params| Binder[Schema Generator]
        Binder -->|2. Send JSON Schema| LLM[LLM Tool Decision]
        LLM -->|3. Output JSON| Adapter[Deserialization Adapter]
        Adapter -->|4. Instantiate Object| Func
    end
    subgraph OpenHands-Security-Guardrails
        Cmd[ACI command input] -->|1. Match patterns| Guard[Security Scanner Hook]
        Guard -->|Safe| Docker[Docker Tmux Execution]
        Guard -->|Unsafe Block| Block[Block execution & Emit SecurityAlert Issue]
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
print("Successfully appended Round 20 to open_source_research.md.")

# Update HTML report
with io.open(report_html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Add Round 20 to sidebar navigation links
nav_target = '<li><a href="#comparison" class="nav-link">📊 跨维度技术矩阵</a></li>'
nav_replacement = '<li><a href="#round14" class="nav-link">R14: smolagents / SK / OpenHands</a></li>\n          ' + nav_target
html_content = html_content.replace(nav_target, nav_replacement)

# Create HTML Section for Round 20
round20_html = u"""      <!-- Round 14 (20th Research) -->
      <section id="round14">
        <h2>R14：代码解释器内存沙箱、原生函数类型适配与命令安全拦截扫网 (smolagents & Semantic Kernel & OpenHands)</h2>
        <div class="product-grid">
          <div class="product-card">
            <div class="product-header">
              <span class="product-title">smolagents, Semantic Kernel 与 OpenHands 的安全控制设计</span>
              <span class="product-meta">Safe Python interpreter, Type adapters & Command scanner</span>
            </div>
            <p><strong>学术与工程突破：</strong></p>
            <ul class="feature-list">
              <li><strong>smolagents · AST 限制性内存解释器 (AST Safe Interpreter)</strong>：开发纯 AST 遍历解释器以在内存中仿真运行 Python 代码，严格限制模块导入和全局变量范围，提供比 Docker 更轻的秒级计算沙盒。</li>
              <li><strong>Semantic Kernel · 原生类型绑定适配器 (Type Binding Adapters)</strong>：解析原生 Python 结构化对象以输出嵌套 JSON Schema，并在 LLM 调用完成后执行反序列化类型映射，打通复杂类型的传递壁垒。</li>
              <li><strong>OpenHands · 安全扫描拦截器 (Security Guardrail Hook)</strong>：在底层 tmux 执行前拦截静态安全违规命令（如 rm -rf / 或读取敏感凭据 env），并在发现异常时直接自动在 issues.json 中记录 security_alert 问题。</li>
            </ul>
          </div>
        </div>
      </section>
"""

# Insert Round 20 section before the comparison matrix section
comparison_target = '<section id="comparison">'
html_content = html_content.replace(comparison_target, round20_html + "\n      " + comparison_target)

# Write updated HTML
with io.open(report_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("Successfully appended Round 20 to open_source_research_report.html.")
