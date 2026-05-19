# 专业做法：一次配置，日常一句

复制粘贴长话术是**入门做法**。团队里更专业的模式是：**配置进项目 + 触发词**，而不是每次重讲三前提。

---

## 推荐架构（三层）

```
┌─────────────────────────────────────────────────────────┐
│  Cursor 多根工作区（可选但强烈推荐）                      │
│  ├─ your-app/          ← 业务代码 + automation/         │
│  └─ qualoop/   ← 方法论（只读，@ 引用无绝对路径） │
└─────────────────────────────────────────────────────────┘
         ▲                          ▲
         │                          │
  .cursor/rules/qualoop.mdc   .cursor/qualoop.json
  （行为契约，复制一次）          （方法论路径，改一行）
```

| 层级 | 做什么 | 频率 |
|------|--------|------|
| **配置** | 规则 + `qualoop.json` +（可选）多根工作区 | **每个业务项目一次** |
| **引导** | 对 Cursor 说「Qualoop 初始化」 | **仅首次** |
| **日常** | 对 Cursor 说「**Qualoop 检查**」 | **每轮一句** |

---

## 一次配置（约 2 分钟）

### 方式 A：安装脚本（最快）

在 PowerShell 中（把路径改成你的）：

```powershell
cd e:/path/to/qualoop
.\scripts\install-cursor-rule.ps1 -TargetProject "D:\your-app" -MethodologyRoot "e:/path/to/qualoop"
```

会在 `your-app/.cursor/` 下生成 `rules/qualoop.mdc` 与 `qualoop.json`。

### 方式 B：手动

1. 复制 `templates/qualoop.cursor.rule.mdc` → `your-app/.cursor/rules/qualoop.mdc`
2. 复制 `templates/qualoop.cursor.json.example` → `your-app/.cursor/qualoop.json`，改 `methodologyRoot`
3. Cursor：**文件 → 将文件夹添加到工作区**，加入 `qualoop` 方法论仓

### 方式 C：团队统一（最专业，**跨计算机必选**）

业务项目在 A 电脑、B 电脑上用 Cursor 开发时，**不要把方法论只放在某一台机器的 `e:\...` 绝对路径里**（另一台机器上没有这条路径）。

**推荐**：在**业务项目仓库**里用 git submodule，路径在每台机器上相同：

```bash
# 在业务项目根目录执行（只需做一次，然后 commit + push）
git submodule add <方法论仓 URL> tools/qualoop
git submodule update --init --recursive
```

`your-app/.cursor/qualoop.json`（提交进业务仓库）：

```json
{
  "methodologyRoot": "tools/qualoop",
  "minValueScore": 60,
  "minQualifiedPerRound": 1,
  "maturity": "L1"
}
```

`your-app/.cursor/rules/qualoop.mdc` 同样 **commit 进业务仓库**。

**另一台电脑首次拉代码后**：

```bash
git clone <业务项目>
cd <业务项目>
git submodule update --init --recursive
```

然后在**该电脑**用 Cursor 打开业务项目文件夹，多根工作区添加 `tools/qualoop`（或只打开业务项目，Agent 读相对路径 `tools/qualoop/METHODOLOGY.md`）。

每台新电脑**不必**再跑安装脚本（若 `.cursor/` 已随 git 同步）；只需保证 submodule 已初始化。

#### 若无 submodule：每台开发机各克隆一份方法论

```bash
# 在开发机 B 上
git clone <方法论仓 URL> ~/Qualoop
```

在**该电脑**对业务项目执行安装脚本，`MethodologyRoot` 填**本机**路径，例如：

```powershell
.\install-cursor-rule.ps1 -TargetProject "D:\your-app" -MethodologyRoot "C:\dev\Qualoop"
```

`qualoop.json` 通常**不要 commit 绝对路径**；优先改用语义 C 的 submodule 相对路径。

---

## 跨计算机对照

| 内容 | 是否随 git 走 | 说明 |
|------|----------------|------|
| 业务代码 + `automation/` | 是 | 在业务仓库 |
| `.cursor/rules/qualoop.mdc` | **建议提交** | 两台机器行为一致 |
| `.cursor/qualoop.json` | **建议提交** | 使用 `tools/qualoop` 相对路径 |
| `tools/qualoop` submodule | **建议** | `git submodule update` 后两台一致 |
| 本机 `e:\20260502_MZH\...` | 否 | 仅当前机器有效 |

---

## 日常怎么用（只对 Cursor 说这些）

| 场景 | 你说 |
|------|------|
| 首次落地 automation | **Qualoop 初始化** |
| 每轮质量检查 | **Qualoop 检查** |
| 上次没高分意见 | **Qualoop 加深检查** |
| 允许按 Issue 改代码（L3） | **Qualoop 执行已分配 Issue** |

**不必**每次 `@` 三份文档、不必粘贴长段落。规则里已写三前提；Agent 需要细节时自行读 `methodologyRoot` 下的 `METHODOLOGY.md`。

---

## 为何这比复制话术更专业

1. **契约持久化**：`.cursor/rules` 是项目资产，可 code review、可进 git，不依赖某人记得住话术。
2. **路径可配置**：`qualoop.json` 一处改路径，避免每台机器绝对路径写死在聊天里。
3. **多根工作区**：`@Qualoop/METHODOLOGY.md` 比绝对路径稳定，也更符合 Cursor 的上下文模型。
4. **触发词稳定**：团队统一「Qualoop 检查」，减少「看看有没有 bug」这类弱指令。
5. **与方法论文仓解耦**：业务仓只留 `automation/` 运行时；方法论升级 submodule 即可。

---

## 不推荐的做法

| 做法 | 问题 |
|------|------|
| 每次聊天粘贴长 prompt | 不可维护、易漏前提 |
| 只打开方法论仓开发业务 | Cursor 会改错仓库 |
| 无 `automation/` 只口头 review | 无 Issue Store、无 Scorer，不算 Qualoop |
| `alwaysApply: true` 且规则过长 | 浪费上下文；用触发词 + 短规则即可 |

---

## 与网页报告的关系

- 开发过程总览：`reports/development-report.html`
- 长话术备查：`references/CURSOR_USAGE.md`
- **日常标准操作本文档**
