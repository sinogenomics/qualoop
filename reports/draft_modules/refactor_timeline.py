# -*- coding: utf-8 -*-
import io
import os
import sys

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

report_path = r"e:\20260502_MZH\Qualoop\reports\development-report.html"

with io.open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize line endings for replacement
original_line_endings = "\r\n" if "\r\n" in content else "\n"
content = content.replace("\r\n", "\n")

# CSS style tag end replacement
css_target = u"""    pre.prompt-body {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      user-select: all;
      cursor: text;
    }
  </style>"""

css_replacement = u"""    pre.prompt-body {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      user-select: all;
      cursor: text;
    }

    /* History Table Styling */
    .history-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin: 1.5rem 0 2rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }
    .history-table th {
      background: var(--surface2);
      color: var(--text);
      font-weight: 600;
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .history-table td {
      padding: 1rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
      font-size: 0.85rem;
    }
    .history-table tr:last-child td {
      border-bottom: none;
    }
    .history-table tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }
    
    .history-table .td-time {
      font-family: var(--mono);
      font-size: 0.78rem;
      white-space: nowrap;
      color: var(--accent);
      display: block;
      margin-top: 0.25rem;
    }
    .history-table .stage-num {
      display: inline-block;
      font-weight: 700;
      color: var(--text);
      font-size: 0.82rem;
      background: var(--surface2);
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      border: 1px solid var(--border);
    }
    
    .history-table .table-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.3rem;
      margin-top: 0.5rem;
    }
    .history-table .table-tags span {
      font-size: 0.68rem;
      padding: 0.15rem 0.45rem;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 4px;
      color: var(--muted);
      border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .sev-badge {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      text-align: center;
      white-space: nowrap;
    }
    .sev-low {
      background: rgba(61, 156, 245, 0.12);
      color: #5ab0ff;
      border: 1px solid rgba(61, 156, 245, 0.25);
    }
    .sev-medium {
      background: rgba(232, 184, 74, 0.12);
      color: #ffcf66;
      border: 1px solid rgba(232, 184, 74, 0.25);
    }
    .sev-high {
      background: rgba(232, 100, 74, 0.12);
      color: #ff8566;
      border: 1px solid rgba(232, 100, 74, 0.25);
    }
    .sev-critical {
      background: rgba(239, 68, 68, 0.12);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.25);
      box-shadow: 0 0 6px rgba(239, 68, 68, 0.15);
    }
    
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .status-yes {
      background: rgba(62, 207, 142, 0.12);
      color: #3ecf8e;
      border: 1px solid rgba(62, 207, 142, 0.25);
    }
    .status-yes::before {
      content: "●";
      font-size: 0.55rem;
      color: #3ecf8e;
    }
    .status-no {
      background: rgba(239, 68, 68, 0.12);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.25);
    }
    .status-no::before {
      content: "●";
      font-size: 0.55rem;
      color: #ef4444;
    }
  </style>"""

if css_target not in content:
    print("Error: CSS target not found in file.")
    sys.exit(1)

content = content.replace(css_target, css_replacement)

# Table section replacement
start_tag = u'<section id="timeline">'
if start_tag not in content:
    print("Error: <section id=\"timeline\"> not found in file.")
    sys.exit(1)

start_idx = content.find(start_tag)
end_tag = u'</section>'
end_idx = content.find(end_tag, start_idx) + len(end_tag)

table_replacement = u"""      <section id="timeline">
        <h2>开发历程</h2>
        <p>汇总与梳理本仓库在迭代与升级中形成的关键里程碑（方法论演进，非业务代码发布）。</p>
        <div style="overflow-x: auto;">
          <table class="history-table">
            <thead>
              <tr>
                <th style="width: 14%; min-width: 110px;">阶段 / 时间</th>
                <th style="width: 25%; min-width: 200px;">升级里程碑</th>
                <th style="width: 12%; min-width: 100px;">严重程度评价</th>
                <th style="width: 25%; min-width: 200px;">存在该问题的影响</th>
                <th style="width: 12%; min-width: 90px;">是否已解决</th>
                <th style="width: 12%; min-width: 90px;">是否推送 GitHub</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <span class="stage-num">阶段 0</span>
                  <span class="td-time">2026-05-22 15:39</span>
                </td>
                <td>
                  <strong>从 LessonVerse 实践中发现共性痛点</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    分散探测、多人/多 Agent 改同一文件、长运行脚本无人看护、Issue 无闭环——需要语言无关的编排方法论，而非绑定单一应用。
                  </div>
                  <div class="table-tags">
                    <span>case-study</span><span>四角色雏形</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-low">低 (30/100)</span>
                </td>
                <td>
                  缺乏统一的质量改进编排模型，导致多 Agent 并行开发冲突和 Issue 无法闭环。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 1</span>
                  <span class="td-time">2026-05-22 16:15</span>
                </td>
                <td>
                  <strong>编写 DEVELOPMENT_GOALS.md，确立 North Star 与命名</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    对外品牌 <strong>Qualoop / 质环</strong>；明确仓库边界（非运行时、非 CI 替代）；定义可观测、可协调、可验证、有节制、可持续五条最终目标。
                  </div>
                  <div class="table-tags">
                    <span>DEVELOPMENT_GOALS</span><span>README</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-low">低 (35/100)</span>
                </td>
                <td>
                  项目定位与最终成功标准不明确，极易偏离开发初衷。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 2</span>
                  <span class="td-time">2026-05-22 16:21</span>
                </td>
                <td>
                  <strong>目标对齐：意见必须朝向最终目标</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    METHODOLOGY §1.3：严谨、审慎、禁止为「表面变绿」削弱检测与锁机制；引入 <code>goal_alignment_note</code>、<code>goal_misaligned</code> 等 Issue 元数据。
                  </div>
                  <div class="table-tags">
                    <span>§1.3</span><span>issue_schema</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-medium">中 (50/100)</span>
                </td>
                <td>
                  大模型生成的修改意见缺乏方向约束，可能为了“表面变绿”削弱核心安全机制。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 3</span>
                  <span class="td-time">2026-05-22 16:21</span>
                </td>
                <td>
                  <strong>每轮必有产出：空轮 = 检查深度不足</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    METHODOLOGY §1.4：每轮须提出缺陷或改进意见；全绿时仍须产出 <code>improvement</code>；空轮触发 channels 扩展、降阈值等加深策略；指标 <strong>empty round rate</strong>。
                  </div>
                  <div class="table-tags">
                    <span>§1.4</span><span>empty_rounds.jsonl</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-medium">中 (55/100)</span>
                </td>
                <td>
                  系统无明显缺陷时会“交白卷”，掩盖了潜在的系统健壮性与架构债务。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 4</span>
                  <span class="td-time">2026-05-22 16:21</span>
                </td>
                <td>
                  <strong>新增 Scorer：按 North Star 贡献度打分</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    模型由四角色扩展为<strong>五角色</strong>；专门智能体 Scorer 对每条意见 0–100 打分，低于合格线不算有效产出；低分轮与空轮同样触发加深检查。
                  </div>
                  <div class="table-tags">
                    <span>Scorer</span><span>scorer_rubric</span><span>value_score</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-high">高 (75/100)</span>
                </td>
                <td>
                  缺乏价值过滤机制，导致大量低价值建议或噪点被分派执行，消耗过多算力。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 5</span>
                  <span class="td-time">2026-05-22 16:21</span>
                </td>
                <td>
                  <strong>网页版开发过程报告（本页）</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    将目标、历程、架构、交付物与采纳路径可视化，便于评审、 onboarding 与对外说明。
                  </div>
                  <div class="table-tags">
                    <span>reports/development-report.html</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-low">低 (25/100)</span>
                </td>
                <td>
                  开发和系统演进的整体情况不透明，评审与新成员加入时无直观指引。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 6</span>
                  <span class="td-time">2026-05-22 18:33</span>
                </td>
                <td>
                  <strong>L3 级成熟度适配、守护进程保活与多角色大模型驱动</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    解决 Windows 系统下跨平台路径锁与租约适配缺陷（QL-001至QL-007）；升级到 L3 成熟度时支持在终端后台自动拉起 Guardian 守护进程（<code>start.bat</code>）以实现 24 小时常驻运行；全面接入本地 Antigravity 大模型驱动五角色，大幅提升自动化诊断与修复决策质量。
                  </div>
                  <div class="table-tags">
                    <span>L3-Compliance</span><span>Guardian</span><span>Antigravity-LLM</span><span>start.bat</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-high">高 (80/100)</span>
                </td>
                <td>
                  路径锁在 Windows 环境下不兼容；终端关闭后自动修复流程极易意外中断。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 7</span>
                  <span class="td-time">2026-05-22 19:00</span>
                </td>
                <td>
                  <strong>模块化评分标准、API 额度预算控制与人机协同告警</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    引入多维模块化评分标准（严重性、对齐度、清晰度、影响度、可验证性）；加入 SWE-agent 风格的 LLM 调用额度与 Token 预算限制类（<code>Budget Limit Exception</code>），防止 Tester 陷入对话风暴；支持降级策略，在预算耗尽或置信度不足时输出 <code>requires_human</code> 告警。
                  </div>
                  <div class="table-tags">
                    <span>Modular-Scoring</span><span>SWE-Agent-Budget</span><span>Token-Limit</span><span>requires_human</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-high">高 (85/100)</span>
                </td>
                <td>
                  大批缺陷并发时极易诱发智能体对话风暴，导致超预期的 API 额度与 Token 瞬间耗尽。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 8</span>
                  <span class="td-time">2026-05-22 19:30</span>
                </td>
                <td>
                  <strong>核心缺陷修复与调度链路元数据对齐 (Critical Debug & Stability)</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    彻底解决 <code>qualoop check</code> 后 Scorer 评分未即时持久化到 issues.json 的缺陷，确保每轮检查结果的即时落库；修正 Scheduler 路径过滤时对 <code>value_qualified</code> 的嵌套读取路径（从 <code>metadata</code> 中正确解包），消除 L3 自动分派和执行阶段的安全隐患。
                  </div>
                  <div class="table-tags">
                    <span>Bug-Fix</span><span>State-Persistence</span><span>Scheduler-Path-Lock</span><span>Value-Qualified</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-critical">严重 (90/100)</span>
                </td>
                <td>
                  状态评分丢失导致合格的 Issue 无法派发；Scheduler 路径解析错误引发 L3 安全隐患，无法自动修复。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 9</span>
                  <span class="td-time">2026-05-22 20:00</span>
                </td>
                <td>
                  <strong>Tester 智能诊断恢复与 Windows 编码兼容性优化</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    完成 Qualoop Tester Agent 的全面诊断与加固：安全恢复新问题发现时的 LLM 智能分析能力，并通过全局 <code>_llm_called</code> 状态锁进行单次调用节流，防止大批量故障检测时引发大模型对话风暴；同时，在 Windows 环境下的遗留脚本子进程调用中注入 UTF-8 环境变量，规避编码解析错误引发的崩溃。
                  </div>
                  <div class="table-tags">
                    <span>Diagnostics</span><span>Global-Throttle</span><span>Windows-Encoding</span><span>Stability</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-critical">严重 (92/100)</span>
                </td>
                <td>
                  中文 Windows 系统下，控制台的 GBK 编码输出引发脚本解析异常崩溃，流程中断。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 10</span>
                  <span class="td-time">2026-05-22 20:30</span>
                </td>
                <td>
                  <strong>Qualoop 系统加固与 ParadigmLearn 全面纠错</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    在 Qualoop 所有自动化运行脚本中注入 sys.path 解析与绝对导入升级，确保可直接在任意目录运行；全面修复 ParadigmLearn 前后端（含 app.py 核心、多语言 setup_i18n、各 JS 及 HTML 文件）多处拼写腐化，恢复正常系统运行与文件上传验证。
                  </div>
                  <div class="table-tags">
                    <span>L1-Observe</span><span>Spelling-Correction</span><span>sys.path-Injection</span><span>Robustness</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-high">高 (80/100)</span>
                </td>
                <td>
                  跨目录运行时 Python 模块导入缺失崩溃；ParadigmLearn 系统拼写错误导致核心业务逻辑彻底断链。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 11</span>
                  <span class="td-time">2026-05-22 21:00</span>
                </td>
                <td>
                  <strong>Planner 与 Scheduler 逻辑校准、Tester 缺陷上报增强与组件编码声明</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    优化 Planner 机制确保大模型生成的里程碑 Issue 评分能在 IssueStore 中即时持久化；修正 Scheduler 嵌套读取 value_qualified 的元数据结构路径，规避 L3 自动分派与执行的安全隐患；增强 Tester 逻辑以捕获 py_compile 超时/错误及缺失关键 app.py 的重大异常并实时写入台账；为 scheduler.py 与 tester.py 补充 coding declaration，全方位提高系统健壮性。
                  </div>
                  <div class="table-tags">
                    <span>Planner-Fix</span><span>Scheduler-Lock</span><span>Tester-Reporting</span><span>Coding-Decl</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-critical">严重 (95/100)</span>
                </td>
                <td>
                  任务分配器结构读取错误，L3 自动执行链路断裂；代码编译异常无法追踪上报。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 12</span>
                  <span class="td-time">2026-05-22 22:01</span>
                </td>
                <td>
                  <strong>多维前沿开源项目深度对标与 47 条升级建议提炼</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    针对多个前沿开源框架（如 smolagents, browser-use, Llama Stack 等）开展十四轮持续深度的调研。从沙盒执行、分层内存、进程内核隔离等维度深入对标，成功提炼 47 项促进 Qualoop 自主进化的升级建议。
                  </div>
                  <div class="table-tags">
                    <span>OpenSource-Research</span><span>Ref-Systems</span><span>Evolution-Roadmap</span><span>Aesthetics</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-medium">中 (60/100)</span>
                </td>
                <td>
                  缺少与行业最前沿成果的对标，难以构建前瞻性的演进地图。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
              <tr>
                <td>
                  <span class="stage-num">阶段 13</span>
                  <span class="td-time">2026-05-22 21:42</span>
                </td>
                <td>
                  <strong>Qualoop 跨目录运行加固与 Windows 终端 Unicode 兼容性修复</strong>
                  <div style="margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);">
                    修复在任意工作目录下直接调用 Python 脚本时的 `sys.path` 绝对导入兼容性问题；解决 Windows 控制台打印 Unicode 字符时的 GBK 编码失败崩溃问题；在 Cookie 导入器中新增通用 `cookies.json` 的扫描和解析，提升在 Windows 环境下的运行鲁棒性，并成功在测试阶段运用桌面图片进行物理文件上传验证。
                  </div>
                  <div class="table-tags">
                    <span>Path-Resilience</span><span>Windows-Unicode</span><span>Cookie-Robustness</span><span>E2E-Image-Upload</span>
                  </div>
                </td>
                <td>
                  <span class="sev-badge sev-high">高 (80/100)</span>
                </td>
                <td>
                  控制台非 ASCII 字符打印崩溃，部分外部依赖 Cookie 缺失导致执行环中断。
                </td>
                <td>
                  <span class="status-badge status-yes">已解决</span>
                </td>
                <td>
                  <span class="status-badge status-yes">已推送</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>"""

content = content[:start_idx] + table_replacement + content[end_idx:]

# Restore original line endings
if original_line_endings == "\r\n":
    content = content.replace("\n", "\r\n")

with io.open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

print("HTML report successfully refactored using Python.")
