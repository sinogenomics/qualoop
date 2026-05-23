# -*- coding: utf-8 -*-
import os
import sys
import io

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

report_path = r"e:\20260502_MZH\Qualoop\reports\open_source_research.md"

with io.open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

timeline_insert = u"""### 📅 第十三次调研（2026-05-23）: 深入分析 TextGrad 的文本反向梯度优化、Promptflow 的多智能体 DAG 编排与批评估、Ragas 的无参考语义相关性与幻觉指标评测

#### 1. TextGrad (斯坦福大学 - 基于自然语言反馈的文本梯度优化框架)
*   **核心创新一：将文本/提示词视为可优化变量 (Treating Prompts/Texts as Optimization Variables)**
    *   *机制原理*：传统 Prompt 调优完全依赖人工经验，或者简单粗暴的 Few-shot 拼接。TextGrad 创新性地引入了类似深度学习“反向传播（Backpropagation）”的理念。它将 Agent 系统中的 System Prompt、代码片段、打分细则统一封装为“变量（Variable）”，并将模型的输出、控制台报错或测试反馈作为“目标损失（Loss）”。
*   **核心创新二：基于自然语言反馈的反向文本梯度传递 (Backpropagation via Natural Language Gradients)**
    *   *机制原理*：在一次运行失败（例如 Executor 修复的代码未通过测试或 Scorer 评分过低）时，TextGrad 并不盲目重试，而是通过大模型对失败进行深入评估，生成具有指导意义的结构化批判（Feedback），这被称为“文本梯度（Text Gradient）”。该梯度会沿着执行逻辑链反向传递（Backpropagated）给处于上游的变量（如 Executor Prompt 或 rules 规约），驱动上游变量以文字重写的方式进行自我更新，实现系统级 Prompt 和指令的自动迭代进化。

#### 2. Microsoft Promptflow (企业级大语言模型工作流编排与评估工具)
*   **核心创新一：声明式 DAG 链路编排与可视化节点构建 (Declarative DAG Workflow with Code-first Integration)**
    *   *机制原理*：Promptflow 将多智能体的执行流定义为标准的有向无环图（DAG），每个节点（Node）可以是 Python 函数、LLM 节点或工具调用。通过 YAML 文件定义输入输出的数据传递管道。这种“代码优先、可视化辅助”的设计不仅实现了逻辑的完全解耦，还支持本地可视化流向追踪。开发者在 Web UI 中可以清晰查看每个节点运行的中间状态与时序拓扑。
*   **核心创新二：离线数据集批处理测试与标准评估管道 (Offline Batch Run & Evaluator Pipelines)**
    *   *机制原理*：为了防范 Prompt 微调导致的级联退化，Promptflow 内建了强大的批处理执行引擎。开发者可以提供包含数百个测试样本的 JSONL 数据集，一键拉起命令行工具运行整个 DAG 流程，并串联专用的评估节点（Evaluators）。评估节点会自动计算宏观统计指标（如修复成功率、准确度、平均 Token 耗用），实现系统级的离线回归测试与质量对齐。

#### 3. Ragas (检索增强生成系统无参考语义评估框架)
*   **核心创新一：无参考的语义多维评估指标 (Reference-free Semantic Metrics)**
    *   *机制原理*：在评估 Agent 上报的建议或编写的代码时，传统 ROUGE/BLEU 指标极度依赖标准参考答案，且无法反映语义真实性。Ragas 提出了多项无参考（Reference-free）语义评测算法：
        1.  *忠实度 (Faithfulness)*：将大模型生成的回答切分为独立断言（Statements），让 LLM 作为裁判，逐条核对这些断言是否能由上下文推导得出，检测是否存在幻觉事实。
        2.  *答案相关性 (Answer Relevancy)*：让 LLM 根据生成的回答逆向生成 3 个可能的问题，计算逆向问题与原问题的语义向量相似度，惩罚答非所问与灌水废话。
*   **核心创新二：合成多维度评测数据集生成器 (Synthetic Test Dataset Generation)**
    *   *机制原理*：缺乏真实的缺陷和测试用例是阻碍系统演进的痛点。Ragas 能够深度解析代码库或文档，利用 LLM 自主发掘语义冲突点，并采用“进化策略”（如将简单问题演化为多步推理问题、条件受限问题），合成高质量、覆盖多维度极具代表性的评测数据集，为自动化评估打下数据底座。

```mermaid
graph TD
    subgraph TextGrad-Optim
        PromptVar[System Prompt Variable] -->|1. Generate Output| RunFix[Executor Code Output]
        RunFix -->|2. Compute Loss| TestSuite{Run Tests / Metric}
        TestSuite -->|Failed: Calculate Text Gradient| FeedbackAgent[LLM Critic / Feedback]
        FeedbackAgent -->|3. Backpropagate natural language gradient| PromptVar
    end
    subgraph Promptflow-DAG
        InputData[Offline Dataset] -->|Batch Executor| FlowDAG[YAML-defined DAG workflow]
        FlowDAG -->|Generate outputs| EvalPipeline[Evaluators Python/LLM]
        EvalPipeline -->|Metrics report| AggReport[Batch Accuracy & MTTR Summary]
    end
    subgraph Ragas-Evaluation
        Context[Context docs / logs] & Answer[Agent Output / Report] -->|Split into assertions| Faith[Faithfulness Evaluator]
        Faith -->|Check Entailment| ScoreF[Faithfulness Score]
        Answer -->|Reverse questions| Rel[Answer Relevancy Evaluator]
        Rel -->|Embedding Similarity| ScoreR[Answer Relevancy Score]
    end
```"""

target_split = u"""    subgraph SWE-bench-Sandbox
        AgentOutput[Agent Output Patch] -->|Apply Git Patch| Container[Git-anchored Docker Sandbox]
        Container -->|Run Test Suite| TestRunner[Test Runner]
        TestRunner -->|1. Verify FAIL_TO_PASS| FixOK[Defect Correctness Check]
        TestRunner -->|2. Verify PASS_TO_PASS| RegressionOK[Regression Prevention Check]
    end
```"""

if target_split not in content:
    target_split = target_split.replace(u'\n', u'\r\n')

if target_split not in content:
    print("Error: target split not found!")
    sys.exit(1)

parts = content.split(target_split)
content = parts[0] + target_split + u"\n\n---\n\n" + timeline_insert + u"\n" + target_split.join(parts[1:])

# Table Row replacements
old_obs = u"""| **可观测与可审计** | 静态生成 markdown 报告与 json 状态 | **OpenHands**: Append-Only Event Stream 日志<br>**Langfuse**: 基于 OpenTelemetry 的分层 Traces 追踪与 Prompt 注册表关联<br>**AgentOps**: 包含会话回放与费率追踪的飞行记录仪监控<br>**LangSmith**: 非侵入式嵌套 Run-Tree 链路追踪与离线数据集评测<br>**Arize Phoenix**: OTel 零侵入追踪与本地嵌入空间投影 | **极极高**：结合 OTel 与 AgentOps 会话回放，引入 LangSmith 风格 of 非侵入式嵌套 Run-Tree 链路捕获与离线回归数据集评测，并支持 Phoenix 本地 3D 嵌入空间可视化分析以防退化。 |"""
new_obs = u"""| **可观测与可审计** | 静态生成 markdown 报告与 json 状态 | **OpenHands**: Append-Only Event Stream 日志<br>**Langfuse**: 基于 OpenTelemetry 的分层 Traces 追踪与 Prompt 注册表关联<br>**AgentOps**: 包含会话回放与费率追踪的飞行记录仪监控<br>**LangSmith**: 非侵入式嵌套 Run-Tree 链路追踪与离线数据集评测<br>**Arize Phoenix**: OTel 零侵入追踪与本地嵌入空间投影<br>**Promptflow**: 离线数据集批处理测试与标准评估管道 | **极极高**：结合 OTel 与 AgentOps 会话回放，引入 LangSmith 风格 of 非侵入式嵌套 Run-Tree 链路捕获与离线回归数据集评测，支持 Phoenix 嵌入空间投影，并利用 Promptflow 实现批评估。 |"""
content = content.replace(old_obs, new_obs)


# Suggestion replacements
old_sugg38 = u"""    > **升级建议三十八（基于 LangSmith 的嵌套 Run-Tree 追踪与离线数据集评测）**：参考 LangSmith，为 Qualoop 引入无侵入式的嵌套 Trace 追踪日志（通过环境变量或修饰器拦截），自动将复杂的五角色协作串联为有向层级 Trace 图。提供离线回归测试套件，允许开发者将线上 Executor 运行产生的问题及修复结果自动提取为评测数据集，进行批量的 LLM-as-a-Judge 自动回归打分，彻底杜绝代码迭代导致的历史功能退化。"""
new_sugg38 = old_sugg38 + u"""
    >
    > **升级建议四十二（基于 Ragas 语义指标的 reference-free 质量与相关性语义评分）**：参考 Ragas，升级 Scorer 对 Executor 交付成果或 Tester 上报质量的打分模块。引入不需要标准参考答案的语义指标评分（如 Faithfulness、Answer Relevance），通过对上下文召回内容 and 模型生成语句进行蕴含分析（Entailment Analysis）与语义相似度分析，防范大模型编写的报告和建议出现言不及义的“灌水”或不切实际的“幻觉建议”。
    >
    > **升级建议四十三（基于 TextGrad 的反馈反向传递与提示词/规则库自动优化）**：参考 TextGrad 框架，将系统内 Scorer 的评分细则和 Planner/Executor 的 Prompt 视为可调优变量。当 Scorer 打分偏低或自动化验证失败时，利用大模型生成关于失败原因和修改方向的“文本梯度”（反馈），并将其反向传播（Backpropagate）至前端 Prompt，以迭代方式自动优化 Prompt 或本地规约，实现质量环的自动化微调与自我进化。"""
content = content.replace(old_sugg38, new_sugg38)

old_sugg41 = u"""    > **升级建议四十一（零拷贝 OpenTelemetry 追踪与 Phoenix 3D 本地嵌入空间可视化）**：参考 Arize Phoenix，为 Qualoop 引入符合标准 OTel 规范的零侵入式代理追踪（Spans 链）。在本地启动嵌入式的可观测 Web UI 以可视化展现运行状态。同时，引入 UMAP 等高维降维算法，将 Executor 生成的代码和 Scorer 评价的 Prompts/Responses 映射到 3D 嵌入空间中，通过特征几何聚类直观分析性能退化的核心成因。"""
new_sugg41 = old_sugg41 + u"""
    >
    > **升级建议四十四（基于 Promptflow 的可视化多智能体 DAG 链路设计与离线批测试）**：参考 Microsoft Promptflow，在 Qualoop 引入 DAG 流向依赖声明。将各个探针、审查器以节点形式可视化组装，并提供强大的本地批处理测试命令行工具。通过配置离线数据集，自动化对不同的 Agent 组合在特定测试场景下的平均 MTTR 和修复率进行回归分析，提升流水线的交付置信度。"""
content = content.replace(old_sugg41, new_sugg41)


with io.open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Report updated successfully with Round 13 findings.")
