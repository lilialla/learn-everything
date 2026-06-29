# learn-everything

<p align="center">
  <img src="assets/learn-everything-logo-anime-girl.png" alt="learn-everything logo" width="220">
</p>

<p align="center"><a href="README.md">English</a> · <b>中文</b></p>

<p align="center">
  <a href="https://github.com/lilialla/learn-everything/actions/workflows/ci.yml"><img src="https://github.com/lilialla/learn-everything/actions/workflows/ci.yml/badge.svg" alt="tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="status: alpha">
  <img src="https://img.shields.io/badge/engine-Python%20stdlib%20%C2%B7%20zero%20deps-3776AB?logo=python&logoColor=white" alt="引擎: Python 标准库·零依赖">
  <img src="https://img.shields.io/badge/spaced%20repetition-FSRS--6-success" alt="间隔复习: FSRS-6">
  <img src="https://img.shields.io/badge/runs%20in-any%20Skill--capable%20AI-7C3AED" alt="运行于: 任意 Skill 宿主">
  <a href="#贡献"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome"></a>
</p>

**一个能同时教你多门学科、而且会记住你的 AI 导师。** 它以技能(skill)形式装进任意支持 Skill 的
AI 助手(Claude Code、Obsidian + Claudian 等)。用大白话跟它对话:它一次只教一个概念,记下你听懂了
什么、在哪儿卡住,并悄悄安排间隔复习,让知识真正留下来。

`状态: alpha` · `许可证: MIT` · `引擎: 纯 Python 标准库(零依赖)` · `测试: CI 全量标准库测试`

> 你往往同时在学好几样东西——一个专业领域、一门考试、一项编程技能——每样需要*不同*的教法,而你一
> 切换就丢了线索。learn-everything 就是为在所有这些之间替你接住这条线索而造。

---

## 它能做什么

- **先教,再出复习卡。** 它以对话方式教你(讲解 → 你试 → 纠正 → 确认),等你真懂了才提炼几张
  复习卡。理解永远先于复习材料。
- **跨轨道编排。** 每门学科是一条"轨道",汇在一块看板下。问一句*"今天我该学什么?"*,它跨所有轨道
  一次性回答——哪些到期该复习、哪条荒废了、哪条临近截止——并排出带时间盒的计划(已在 25+ 并行轨道下
  测过;用 `set-prefs` 调任一轨道的权重或时长块)。
- **它把你当作学习者来记住。** 每次会话都留下一份记忆摘要、你的误解、你问过的术语、以及续学指针——
  几天后它能还原*"你学了什么、在哪卡住、下一步做什么"*。
- **一套真正的教学法工具箱。** 有循证依据的教学方法——7 个可独立使用(精读带学、苏格拉底、费曼、
  worked examples、刻意练习、主动回忆、精加工)+ 3 个可叠加层(双重编码、元认知、静默的学习者模型)。
  导师按材料 × 学习者 × 目标来选——是模型的判断、依方法文件里的启发式,**不是写死的选择器**。
- **跨宿主的技能设计。** 它以技能形式运行在任意支持 Skill 的 AI 助手中。推荐的一种用法是
  Obsidian + Claudian 插件(左边读、右边跟导师对话,笔记实时长进你的库);用 Claude Code 也可以。
  全是你自己的 markdown。
- **默认隐私 + 零依赖。** 你的轨道文件留在本地并被 gitignore;当你要求导师学习某个来源时,该来源正文会发送给你正在使用的宿主模型;引擎本身是纯 Python 标准库——无需 `pip install`。

## 你会得到什么

- 一个任意学科、用你母语对话的导师。
- 自动、持久的笔记 + 每条轨道的"内容地图"。
- 间隔复习(FSRS-6),安排复习时点,让知识留存。
- 一份跨所有学科、带时间盒的"今天学什么"计划。
- 被捕捉的误解会**反哺**——下次先复查你的弱点,并纠正教学路线。
- 提问热力图——看你对哪些概念问得最多(你的弱点/重点)。
- 看得见的进度:学了多少卡、多少卡锁进长期记忆、本周正确率。

## 快速上手(直接跟它说话)

learn-everything 是一个装进任意支持 Skill 的 AI 助手的技能,用大白话对话即可——你完全不碰命令行。
下面的步骤用 **Obsidian + Claudian 插件**,这是推荐的一种用法;若你已经在用 Claude Code,把它指向
本文件夹,直接跳到跟导师对话即可。

**第一天 — 一次性安装(约 10 分钟):**

1. **拿到文件:** `git clone https://github.com/lilialla/learn-everything.git`。
2. **在 Obsidian 打开:** *打开文件夹作为库* → 选 `learn-everything` 文件夹。
3. **装 [Claudian](https://github.com/YishenTu/claudian) 插件**(社区插件 → 搜 "Claudian" → 安装 → 启用)。
   它在右侧栏放一个能读写你库的 AI 导师。
4. **(macOS)若 Claudian 报 401 / 认证错误:** 它内置的 Claude 需要一份凭证。终端跑 `claude setup-token`,
   把 token 填进 Claudian 设置的 `CLAUDE_CODE_OAUTH_TOKEN`。(若你用 Claude Code 订阅登录,也可把
   keychain 凭证导出到 `~/.claude/.credentials.json`。)
5. **(可选)原生复习:** 装 [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition),
   导师做的卡片也能在 Obsidian 里直接复习。

**然后只管在右侧栏跟导师说话** —— 无需记任何命令:

- *"我想学 &lt;某主题&gt;"* / *"教我这篇文章"*(粘贴或打开它)
- *"接着上次继续"*
- *"考考我"* · *"今天我该学什么?"* · *"我学得怎么样?"*

它一次教一个概念,边教边把笔记写进你的库,并安排复习让知识真正留下。

**下次回来:** 打开库问一句*"今天我该学什么?"*——它会先告诉你所有学科一共多少卡到期。(想不打开也被提醒?
`python3 scripts/registry.py nudge` 打印一行大白话——*"learn-everything: 7 cards due across 3 subjects …"*
——放进 Daily Note、shell 登录提示或定时任务/cron 即可。无需后台守护进程。)

## 工作原理

```
        你说话(大白话)
              │
   ┌──────────▼───────────┐     教 → 听懂 → 提炼卡片 → 复习 → 续学
   │  learn 技能(宿主适配) │     读你的话、调引擎、按教学法走
   └──────────┬───────────┘
   methods/*.md │ scripts/*.py
   (怎么教)     │ (确定性状态:排程、文件、看板)
              ▼
         tracks/<id>/   ← 你的学习,纯 markdown,归你所有
```

干净地分两层:

- **可移植内核** —— 确定性引擎(`scripts/`:FSRS 排程、逐轨状态文件、状态看板、每日计划器),只用
  Python **标准库**,外加一层**方法层**(`methods/*.md`)——教学法模板,纯 markdown 数据。
- **宿主适配器** —— 主要入口是一个很薄的 Claude Code 技能(`skills/learn/`),把你的大白话变成引擎调用和教学循环。
  **技能本身不是智能:**宿主模型按方法层执行教学,引擎只负责把状态管真(它绝不瞎猜到期日或卡片 id)。
  `mcp/server.py` 是同一内核之上的可选 MCP 宿主适配器。

## 教学法工具箱

教学方法是**数据**(`methods/*.md`)。导师按 材料 × 学习者 × 目标 读取并依方法文件里的启发式来选——
是模型的判断、**不是写死的选择器**——你只会看到结果("我带你过一遍" / "我考考你" / "你讲给我听")。
工具箱 = **7 个可独立使用的教学法** + **3 个可叠加层**(`dual-coding`、`metacognition`、`learner-model`,
融进其它方法)+ 一个横切的 `learning-science`;`exam` / `applied` / `reading-guide` 模式则定调整条轨道。

| 方法 | 适用 |
|---|---|
| `tutor` | 精读带学——知识/说明性材料的默认 |
| `socratic` | 以提问引导,让你自己发现答案 |
| `feynman` | 你讲回来,模型追问漏洞 |
| `active-recall` | 检索练习式测验——复习默认(FSRS 的搭档) |
| `worked-examples` | 程序性 / 数学 / 编程——先看解好的例题,再逐步撤掉脚手架 |
| `deliberate-practice` | 练成一项可执行技能:锁定边缘、刻意练、即时反馈 |
| `elaboration` | 已掌握者的上行挑战(迁移、边界、压缩) |
| `dual-coding` | 文字配图、概念交错 |
| `metacognition` | 先预测再对照、计划/监控/评估、识破"假会了" |
| `learner-model` | 每轮静默判读掌握度/误解/负荷,引导每一步 |
| `learning-science` | 横切的"为什么":使命、最近发展区、长期留存 |

## 记忆与可追溯

learn-everything 让你的学习留下持久、可查的痕迹——全是纯 markdown:

- **`CONTEXT.md`**(每轨)—— 续学时先读的滚动摘要:*在哪 / 学了什么 / 已知卡点 / 待续线索。*
- **`learning-records/`** —— 带日期、只追加的洞见(每次纠正的误解、已有知识、展示的掌握)。
- **`glossary.md`** —— 你问过的术语(一问就记,会用了再升级);也是一张"哪里难"的地图。
- **提问热力图** —— 每个零散提问按概念记录;`questions` 排出你问得最多的地方(弱点/重点),反哺重教与出卡。
- **`progress`** —— 每轨三个留存数字:总卡数 / 已固化(进长期记忆)/ 7 日正确率。
- **来源可追溯** —— 每张卡可带 `source`(出自哪个笔记 / 链接 / 页码),任何事实都能回溯到出处。
- **闭环收尾校验** —— `session-check --strict` 校验会话是否留下"卡或理由、log 行、next_action、
  今日更新的 CONTEXT.md";导师会跑它、未通过前不宣布完成,记忆才真正留得住(且摘要有上限,不会随着
  月复一月而上下文过载)。

被捕捉的误解会**反哺**:下次先复查你的卡点、纠正路线——已掌握的略过、错过的加重、旧的失误换个角度重教。

## 数据模型

**唯一真实来源**是 `tracks/` 下的逐轨文件夹;根目录的 `registry.json` 只是**可重建缓存**——随时能从
`TRACK.md` 重新生成。

```
tracks/<id>/
  TRACK.md            # 真实来源:YAML frontmatter(id、title、mode、pedagogy、status、
                      #   created、deadline、last_active、next_action)+ "## Goal" + "## Log"
  MISSION.md          # 这条轨道的真实"为什么"(为每次会话定锚)
  CONTEXT.md          # 滚动记忆摘要(续学先读)
  plan.md             # 内容地图:会话 + 卡片 wikilink
  cards/card-0001.md  # frontmatter + "#flashcards/<track>" + 问题 / "?" / 答案(兼容 Obsidian 间隔复习)
  notes/<date>-*.md   # 你在读的原文 + 导师讲义笔记
  learning-records/   # 带日期的决策级洞见(纠正的误解等)
  glossary.md         # 你问过的术语(一张"哪里难"的地图)
  review-state.json   # FSRS 边车:每卡 stability/difficulty/due/reps/lapses/last_review/state
  review-log.jsonl    # 只追加的评分历史
  questions-log.jsonl # 只追加的零散提问(热力图来源)
  curriculum.json     # 整本书的教学状态(分块清单 + 已教/待教),加载书时生成
  fsrs-weights.json   # 可选:从你的复习历史拟合的个性化 FSRS 权重

registry.json         # 所有轨道的可重建缓存(绝不是唯一来源)
```

**引擎**(`scripts/`)写:`TRACK.md` frontmatter/Log、`cards/`、各 `*.json`/`*.jsonl` 边车、
`curriculum.json` 与 `registry.json`。**导师**(技能)写人类可读的记忆——`MISSION.md`、`CONTEXT.md`、
`plan.md`、`notes/`、`learning-records/`、`glossary.md`——都是纯 markdown(无 CLI)。`registry.json`
或某个 `review-state.json` 丢失/损坏时,引擎会重建 / 优雅降级并告警到 stderr——绝不丢失真实来源、绝不
让整次运行崩溃。整文件写入是原子的(临时文件 + 改名),在 Google Drive / Dropbox 同步下安全。

<details>
<summary><b>边车 JSON 结构</b></summary>

- `review-state.json` —— `{ "<card-id>": {stability, difficulty, due, reps, lapses, last_review, state} }`
- `review-log.jsonl` —— 每次评分一行:`{date, card, grade, due, reps, lapses, state}`
- `questions-log.jsonl` —— 每个提问一行:`{date, concept, question, term?}`
- `curriculum.json` —— `{title, source_file, structure_source, built, max_chars, total, position, chunks:[{chunk_id, title, heading_path, page_range, start, end, char_len, status, taught_on}]}`
</details>

<details>
<summary><b>CLI 参考(导师替你调,你很少需要直接用)</b></summary>

引擎是三个标准库脚本。`registry.py` 管所有状态;`structure.py` 管长文档切分 + 整本书课程表;
`fsrs.py` 是调度器。

```bash
# 概览与计划
python3 scripts/registry.py status [--today YYYY-MM-DD]        # 看板,先报到期卡数
python3 scripts/registry.py nudge                             # 一行大白话报到期(daily-note/cron)
python3 scripts/registry.py plan-day [--minutes N] [--energy low|normal|high]
python3 scripts/registry.py progress [--track <id|all>]        # 总数 / 已固化 / 7日正确率

# 建轨、调优与门禁
python3 scripts/registry.py create-track --id <id> --title <t> --mode domain --pedagogy <p> [--deadline YYYY-MM-DD] [--goal "..."]
python3 scripts/registry.py set-prefs --track <id> [--goal-weight N] [--minutes-per-new-block N]
python3 scripts/registry.py ingest-check --track <id>          # 可以开学了吗?(MISSION 填了吗)
python3 scripts/registry.py session-check [--strict [--review]] --track <id>   # 收尾门禁(strict = 卡+log+next+今日CONTEXT)

# 卡片与复习
echo '[{"question":"...","answer":"...","tags":["L2"],"source":"..."}]' | python3 scripts/registry.py add-cards --track <id>
python3 scripts/registry.py due [--track <id|all>] [--today YYYY-MM-DD]
python3 scripts/registry.py leeches --track <id>              # 反复错的卡——重教,别再测
python3 scripts/registry.py grade --track <id> --card <card-id> --grade <1-4> [--today YYYY-MM-DD]

# 记忆与信号
python3 scripts/registry.py log --track <id> --what "..." [--next "..."] [--no-cards-reason "..."]
python3 scripts/registry.py log-question --track <id> --concept "<C>" --question "<Q>" [--term "<T>"]
python3 scripts/registry.py questions [--track <id|all>]       # 你问得最多的地方,排行
python3 scripts/registry.py rebuild                            # 从 TRACK.md 重建 registry.json

# 长文档(整本书):切分 → 逐块教、可续学
python3 scripts/structure.py split <file.md> [--max-chars N]
python3 scripts/structure.py curriculum-build --track <id> <source.md>
python3 scripts/structure.py next-chunk --track <id>          # 下一个待教块 + 其原文
python3 scripts/structure.py mark --track <id> --chunk <chunk-id>
python3 scripts/structure.py curriculum-status --track <id>   # 已教 / 剩余 / %

# 调度器(由 registry.py 调用;也可单独用)
python3 scripts/fsrs.py schedule --state '<json|->' --grade <1-4> --now YYYY-MM-DD
```

(工具/管理类:`add-card` 单卡、`next-card-id`——很少需要直接用。)

评分:`1`=Again `2`=Hard `3`=Good `4`=Easy。省略 `--today` 时取系统当天。
</details>

## 隐私与保密

> **学习任何敏感内容前,先读这段。**

- 录入一个来源时,**它的正文会被发送给宿主模型**(Claude)。不要录入你无权发送给第三方模型的材料;
  涉密/客户/法律文件先确认授权。
- 你的学习放在 `tracks/`,已被 **gitignore**——笔记、卡片、提问、记忆都只留本地,绝不会被误提交。
  `profile.md`、`registry.json`、`.obsidian/`、`.claudian/`(可能含你的认证 token)也都被 gitignore。
- 录入的来源文本一律按**数据,而非指令**处理——文档/网页里嵌入的祈使句是要分析的内容,绝不是要执行的命令。

## 关于 FSRS

引擎用纯标准库 Python 实现了 **FSRS-6** 间隔复习。它经过**行为验证**(测试锁定打分顺序、到期日单调性、
新卡初始化);与参考实现的精确数值对齐被刻意延后——目标是正确、可预测、有良好测试覆盖的排程,而非逐位
复刻常数。个性化权重在有真实复习历史前不在范围内。

## 项目结构

```
skills/learn/SKILL.md     主要 Claude Code 技能适配器(含 FEEDBACK.md 改进日志)
methods/*.md              教学法工具箱(数据,非代码):7 独立 + 3 叠加层 + 模式
scripts/registry.py       所有轨道/卡片/registry/计划器状态读写(标准库)
scripts/structure.py      长文档切分 + curriculum 状态机(标准库)
scripts/fsrs.py           FSRS-6 调度器(标准库)
scripts/security_check.py 仓库 secret + 隐私 ignore 检查
adapters/                 可选 out-of-core 摄入/搜索/优化适配器
adapters/safety.py        共享非可信数据边界 + 注入扫描规则
mcp/server.py             同一内核之上的可选 MCP 宿主适配器
tests/                    单元测试(CI 全量 discovery)——引擎 + 适配器 + 长文档课程表
plans/                    设计规格、功能设计、架构/优化计划
docs/                     审计 + 架构优化计划
tracks/                   你的学习数据(已 gitignore)
```

## 路线图

原先的待建 backlog 现已**以 out-of-core 适配器 + 新模式的形式构建完成(alpha)**,使标准库内核保持零
依赖、CI 保持全绿:

- **`exam` 与 `applied` 轨道模式** —— `methods/exam.md`(大纲 → 学习 → 测验 → 模考,朝一个有日期的目标)
  与 `methods/applied.md`(在动手中学,捕捉踩坑点)。
- **URL 摄入**(`adapters/url_ingest/`)—— 给一个链接 → 清洗成原文 markdown → 走正常教学循环。网页路径
  端到端可用;视频(B站/YouTube/抖音)与微信公众号使用内嵌于 [`providers/`](providers/README.md) 的
  **vendored 抓取器**,使克隆开箱即用(运行时依赖按需安装);PDF 交给文档适配器。
- **长文档摄入 + 课程表** —— `scripts/structure.py` 把整本书切成层级,`methods/reading-guide.md`(导读)
  把它变成经审批的大纲,再由**课程状态机**(`curriculum-build` → `next-chunk` → `mark` →
  `curriculum-status`)**一次一块、跨天可续地**逐个知识点教完;`adapters/doc_ingest/` 负责 OCR/抽取。
- **联网搜索**(`adapters/web_search/`)—— 可选、out-of-core:授课中补缺口或核查论断;结果以 UNTRUSTED
  数据返回,供权衡与引用(惰性后端,不进内核依赖)。
- **MCP server**(`mcp/server.py`)—— 用同一引擎驱动任意支持 MCP 的宿主。
- **个性化 FSRS 权重**(`adapters/fsrs_optimize/`)—— 从你自己的复习历史拟合权重;`scripts/fsrs.py` 若
  存在逐轨 `fsrs-weights.json` 会自动加载。

> **Alpha 提示:** 带依赖的路径(实时网页抓取、OCR、MCP 握手、torch 优化器)已接好并在缺少可选依赖时
> 优雅降级,但尚未对真实输入做规模化检验——依赖前请先验证。指导原则不变:别让广度跑在黏住的核心循环
> 之前。完整设计见 [`plans/specs/2026-06-22-feature-designs.md`](plans/specs/2026-06-22-feature-designs.md)。

## 状态与诚实说明

这是 **alpha**。已扎实并测过的:确定性引擎、完整状态机、每个 CLI、所有文件产物——由 unittest 全量
发现、MCP smoke、secret check 与既有手工从零验收共同覆盖。只有真实会话能证明的:**教学对话本身的质量**(取决于宿主模型)。
它还没经过数月、多学科的实战检验——那是下一个里程碑,不是构建任务。

## 贡献

欢迎 issue 与 PR。请守住不变量:内核保持纯标准库零依赖;markdown 文件是唯一真实来源(`registry.json`
是可重建缓存);卡片保持兼容 Obsidian 间隔复习;先教学后出卡;未经学习者批准不落库。新教学法就是一个新的
`methods/*.md`。提交前请跑 `python3 -m unittest discover -v`、
`python3 -m unittest mcp.test_server -v` 和 `python3 scripts/security_check.py --history`。

## 致谢

- `methods/learning-science.md` 的教学法改编自 [Matt Pocock 的 `teach` skill](https://github.com/mattpocock/skills)
  (MIT,© 2026 Matt Pocock)——按 learn-everything 的 track/card/FSRS 模型重写。
- FSRS 排程遵循 [open-spaced-repetition/py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)(FSRS-6);
  卡片兼容 [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition);
  Obsidian 内体验由 [Claudian](https://github.com/YishenTu/claudian) 提供。
- [`providers/`](providers/README.md) 下的内嵌抓取器:`wechat-article-fetch`(MIT,© 2025 杨卫薪律师
  —— `LICENSE.txt` 原样保留)与 `video-notes`(保留其个人学习用途声明)。原样使用,把链接转成可学习的来源。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
