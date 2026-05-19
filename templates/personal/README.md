# `templates/personal/` — 个人级 AI 规则

> 把 Qualoop 接入「**用户级**」AI 配置，而不是「项目级」。
> 配一次，**所有新项目自动生效**，新项目首句话术只剩 `Qualoop 接入，开发目标见 <path>`。

主文件：[`qualoop.personal-rule.md`](./qualoop.personal-rule.md)

里面给出了：

- **粘贴位置表**（Cursor / Claude Code / Codex CLI / Gemini CLI / Aider / Amp）
- 一段**统一的个人规则文本**（粘贴到任一上述位置）
- 接入后的**极简日常话术**

## 何时用项目级、何时用个人级

| 场景 | 选哪种 |
|------|--------|
| 你自己几乎所有项目都用 Qualoop | **个人级**（本目录） |
| 团队多人协作，需要保证人人一致 | 个人级 + **项目级 AGENTS.md** 双保险 |
| 单次试用、临时项目 | 项目级 only（见 [BOOTSTRAP.md](../../BOOTSTRAP.md)） |

两者并不冲突；同时存在时**项目级 `AGENTS.md` 优先**，个人级只在没有项目契约时触发接入流程。
