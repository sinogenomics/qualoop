# 在 Cursor 业务项目中如何使用 Qualoop

> **专业做法（推荐）**：见 **[PROFESSIONAL_SETUP.md](./PROFESSIONAL_SETUP.md)** — 一次配置，日常只说「**Qualoop 检查**」。  
> 下文长话术仅作备查，不必每次复制。

**本仓库路径（请按你机器修改）**：`e:/path/to/qualoop`

**一键安装规则**（PowerShell）：

```powershell
cd e:/path/to/qualoop
.\scripts\install-cursor-rule.ps1 -TargetProject "D:\your-app" -MethodologyRoot "e:/path/to/qualoop"
```

---

## 日常一句（配置完成后）

| 你说 | 含义 |
|------|------|
| **Qualoop 初始化** | 首次在本项目建 `automation/` |
| **Qualoop 检查** | 跑一轮（三前提 + Scorer） |
| **Qualoop 加深检查** | 低分/空轮后加深 |

---

## 备查：手动 @ 引用（无规则时）

1. 用 Cursor 打开 **业务项目**。
2. `@` 引用方法论：`DEVELOPMENT_GOALS.md`、`METHODOLOGY.md`。
3. 或将方法论文件夹 **添加到工作区**（多根工作区）。

---

## 话术 1：第一次在业务项目接入（复制整段）

```
本项目要接入 Qualoop（质环）。

方法论仓库（只读参考，不要改里面的文件）：
e:/path/to/qualoop

请先阅读：
@tools/qualoop/DEVELOPMENT_GOALS.md 的「§零 首要前提」
@tools/qualoop/METHODOLOGY.md 的 §1.3–§1.5 与 §2 五角色
@tools/qualoop/ADOPTION_GUIDE.md 的 Phase 0–1

然后只在【当前业务项目】里：
1. 创建 automation/
2. 按 templates/config.example.json 生成 automation/config.json，并填入本项目的 health URL、app.name、测试命令
3. 实现最小 L1：IssueStore（fingerprint 去重）+ Tester + Scorer + reports/latest_issues.md
4. 遵守三前提：目标对齐、每轮必有产出、Scorer 打分且 value_score≥60（可配置）才算合格
5. 不要自动大范围改业务代码；L1 只观察与记录

完成后告诉我：如何运行 tester --once / scorer --once，以及 issues.json 里当轮合格意见有几条。
```

---

## 话术 2：每轮检查（开发过程中最常用）

```
按 Qualoop 在本项目跑【一轮】质量检查（不是普通 code review）：

@tools/qualoop/METHODOLOGY.md §1.3–§1.5

必须满足：
1. 提出至少 1 条修改意见（缺陷或 improvement），不能只回复「没问题」
2. 每条意见写 goal_alignment_note，说明如何服务本项目 North Star
3. 由 Scorer 逻辑打分（0–100），记录 value_score；低于 60 的算不合格意见
4. 当轮至少 1 条 value_qualified；否则加深检查（更多测试/lint/覆盖盲区），直到有合格高分意见
5. 意见不得背离目标（禁止为通过而删测试、关检测）

输出：
- 更新或写入 automation/issues.json（或等价台账）
- 生成 automation/reports/latest_issues.md 摘要
- 列出：合格意见数、最高分、未合格原因
```

---

## 话术 3：检查深度不够（空轮 / 低分）

```
上一轮 Qualoop 检查不合格：没有足够高分（value_qualified）意见。

请加深检查，直到至少 1 条 value_score ≥ 60 且对齐 North Star 的意见：
- 扩展 discovery：单元测试、lint、E2E、依赖/文档漂移
- 全绿时也必须写 type: improvement（覆盖、可观测性、自动化健康等）
- 参考 @tools/qualoop/METHODOLOGY.md §1.4.2

不要宣布「系统健康无需修改」。
```

---

## 话术 4：让 Cursor 按高分意见改代码（L3，慎用）

```
仅处理 automation/issues.json 里 value_qualified=true 且已分配的 Issue。

@tools/qualoop/METHODOLOGY.md §2.4 Executors

要求：
- 遵守 fixer 策略表；health/static 默认只记录不瞎改
- 改完后 verifier 复跑同一 discovery channel
- 无法验证则 resolved=false，不要标记已解决
```

---

## 话术 5：加一条项目规则（可选，对 Cursor 说）

```
请在本项目 .cursor/rules/ 下新增 qualoop.mdc（alwaysApply: true），
内容要求：凡用户说「Qualoop」「质环」「跑一轮检查」时，
必须执行三前提（对齐、必有产出、Scorer 合格分），并引用方法论路径
e:/path/to/qualoop。

可参考 @tools/qualoop/templates\qualoop.cursor.rule.mdc
```

---

## 不要这样对 Cursor 说

| 模糊说法 | 问题 |
|----------|------|
| 「帮我看看有没有 bug」 | 不会走 Issue Store、Scorer、三前提 |
| 「代码 review 一下」 | 可能交白卷，无 value_score |
| 「有问题再改」 | 不会强制每轮必有产出 |

**建议**：固定使用「按 Qualoop 跑一轮检查」触发完整流程。

---

## 方法论仓 vs 业务仓

| 仓库 | 放什么 |
|------|--------|
| qualoop（方法论仓） | 文档、templates、本说明 |
| 你的业务项目 | automation/ 运行代码、config.json、issues.json、reports/ |

Cursor 默认在**当前打开的工作区**写代码；话术里写清楚「只在当前业务项目修改」。
