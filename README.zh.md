# learn-everything（多轨学习操作系统）

一个开源的、人机协作的**多轨学习操作系统**。它让一个人同时学习很多不同的东西——考试备考、
开放式的专业领域、动手类技能——全部汇总在一块状态看板下。由宿主模型（今天是 Claude）负责
*教学*（苏格拉底式提问、费曼讲解回放、主动回忆），由一个小而确定的引擎负责*把状态管好、管真实*。

## 它和别的工具有什么不一样

大多数学习工具一次只管一个主题：一个抽认卡 App、一个单科辅导、一套间隔复习卡组。它们共同
缺的，是**跨轨编排**——这恰恰是你真正会遇到的难题：你同时在学五样东西，每一样还是不同*类型*，
一切换轨就丢上下文。

learn-everything 围绕两个现有工具没有结合起来的核心想法构建：

- **跨轨编排**——所有活跃的学习轨道都汇总在一块可重建的状态看板下。你问「接下来该做什么？」，
  系统会跨所有轨道一次性回答：哪些卡片到期该复习、哪条轨道停滞了、哪条临近截止日期。
- **逐轨教学法**——每条轨道自己选择希望被怎样教（苏格拉底 / 费曼 / 主动回忆）。教学方法是
  *数据*，不是写死的行为，因此一条领域轨道和一条考试轨道可以用完全不同的方式来追问。

## 设计：内核 + 适配器

系统分为**可移植内核**和一层很薄的**宿主适配器**。可移植内核是一个确定性引擎（FSRS 排程、
逐轨状态文件、状态看板），只用 Python 标准库编写——不依赖 `pip`，不含任何 Claude 专属代码——
再加上一层*方法层*，即一组以 markdown 数据文件形式存在的教学法模板；今天的宿主适配器是一个
轻量的 Claude Code 技能（`skills/learn/`），它通过读取 `TRACK.md` 文件、调用引擎来编排
创建 / 录入 / 复习。**插件本身不是智能：** 宿主模型按方法层执行教学，引擎只提供确定性的支撑结构。
MCP 服务器与其他宿主适配器属于后续工作——内核的接口设计已经为它们预留了不需重写的接缝。

## 快速上手

learn-everything 开箱即用配合 **Claude Code**——把它指向 `learn` 技能即可。

```bash
# 1. 克隆
git clone <你的仓库地址> learn-everything
cd learn-everything

# 2. 在 Claude Code 中使用，调用 skills/learn/ 技能
#    （在会话里直接说「开一条学习轨道」/「复习一下到期的卡片」即可）

# 3. 创建一条轨道
python3 scripts/registry.py create-track \
  --id llm-agents --title "LLM 与智能体" --mode domain --pedagogy socratic \
  --goal "搞懂现代智能体架构"

# 4. 录入一个来源（宿主模型提出候选卡片，你确认后写入）
#    然后加入一张已确认的卡片：
python3 scripts/registry.py add-card --track llm-agents \
  --question "FSRS 排的是什么？" --answer "每张卡片的下次复习日期。" --tags fsrs

# 5. 查看到期卡片，然后打分
python3 scripts/registry.py due --track all
python3 scripts/registry.py grade --track llm-agents --card card-0001 --grade 3
```

所有内容都是你能直接读、改、自行版本管理的纯文本文件。

## 在 Obsidian 里用（一个软件搞定）

learn-everything 的文件夹本身就是一个合法的 Obsidian 库（markdown + frontmatter +
`[[wikilink]]` + 每条轨道的 `plan.md` 内容地图），所以你可以在一个窗口里跑完整个流程：

1. **把仓库作为库在 Obsidian 中打开**——左边渲染原文笔记、卡片和 `plan.md`。
2. **装 [Claudian](https://github.com/YishenTu/claudian)**（MIT）：它把 Claude Code 嵌成侧边栏，
   以该库为工作目录。这个侧栏就是你的导师——左边读、右边问，笔记实时长进 `tracks/<id>/notes/`。
3. **装 [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition)**
   （MIT）：`add-card` 写出的卡片采用它的 `#flashcards/<track>` + `?` 分隔格式，可在 Obsidian
   里原生复习。learn-everything 的 FSRS 引擎仍是权威排程器（状态存在 `review-state.json`）。

> ⚠️ **请在你的机器上验证一次：** Obsidian 内一体化路径依赖 Claudian 嵌入的 Claude Code 能通过
> Bash 跑我们的 Python 引擎。理论上可行但未经验证——用
> `python3 scripts/fsrs.py schedule --state '-' --grade 3 --now 2026-06-22` 测一下。若脚本执行
> 被沙箱拦截，就改用「终端里的 Claude Code + 旁边开 Obsidian（同一文件夹）」。

## 数据模型

**唯一真实来源**是 `tracks/` 下的逐轨文件夹。仓库根目录的 `registry.json` 只是**可重建的缓存**
——它随时可以从各个 `TRACK.md` 文件重新生成。

```
tracks/<id>/
  TRACK.md            # 唯一真实来源：YAML frontmatter（id、title、mode、pedagogy、
                      #   status、created、deadline、last_active、next_action）
                      #   + "## Goal" + "## Log" 表格
  cards/
    card-0001.md      # frontmatter（id、tags）+ "#flashcards/<track>" + 问题 / "?" / 答案
                      #   （兼容 Obsidian 间隔复习插件，可在 Obsidian 里原生复习）
  notes/
    <date>-<slug>.md  # 自由形式的学习笔记
  plan.md             # 内容地图（MOC）；用 wikilink 链接到卡片
  review-state.json   # FSRS 边车文件：每张卡的 stability/difficulty/due/reps/lapses/state

registry.json         # 所有轨道的可重建缓存（绝不是唯一来源）
```

卡片 id 按轨道补零、顺序递增。新卡片以 FSRS `state="new"`、`due=today` 初始化。如果
`registry.json` 或某个 `review-state.json` 丢失或损坏，引擎会自动重建 / 优雅降级，并把警告写到
stderr——它绝不丢失真实来源，也绝不让整次运行崩溃。

## 命令行接口

引擎就是两个脚本。技能会调用它们，你也可以直接用。

`scripts/fsrs.py`

| 命令 | 用途 |
| --- | --- |
| `schedule --state '<json\|->' --grade <1-4> --now YYYY-MM-DD` | 打印某张卡片新的 FSRS 状态。`--state '-'`（或省略）= 全新卡片。打分：1=Again、2=Hard、3=Good、4=Easy。 |

`scripts/registry.py`

| 命令 | 用途 |
| --- | --- |
| `create-track --id <id> --title <t> --mode domain --pedagogy <p> [--deadline YYYY-MM-DD] [--goal "..."]` | 搭建一条新轨道的文件夹并更新缓存。 |
| `rebuild` | 重新扫描 `tracks/*/TRACK.md`，重写并打印 `registry.json`。 |
| `status [--today YYYY-MM-DD]` | 先重建，再打印看板：每条轨道 + 距截止天数 + 今日到期卡片数 + 是否停滞。 |
| `next-card-id --track <id>` | 打印下一个可用卡片 id（如 `card-0004`）。 |
| `add-card --track <id> --question "..." --answer "..." [--tags a,b] [--today YYYY-MM-DD]` | 写入一张新卡片并初始化其复习状态。 |
| `due [--track <id\|all>] [--today YYYY-MM-DD]` | 列出到期卡片（`due <= today`）。 |
| `grade --track <id> --card <card-id> --grade <1-4> [--today YYYY-MM-DD]` | 用 FSRS 给卡片打分，更新复习状态与 `last_active`。 |
| `log --track <id> --what "..." [--next "..."] [--artifacts "..."]` | 追加一行 `## Log`，并更新 `last_active` / `next_action`。 |

`registry.py` 在打分时导入 `fsrs.py`。省略 `--today` 时默认取系统当天日期。

## 保密与隐私

> **在录入任何敏感内容之前，请先读这一节。**

- 当你录入一个来源时，**它的正文会被发送给宿主模型**（Claude）以生成候选卡片。不要录入你无权
  发送给第三方模型的材料。
- 整个 `tracks/` 目录都被 **gitignore**——你的学习数据、笔记和卡片只留在本地，绝不会被误提交。
  仅有 `tracks/.gitkeep` 被纳入版本管理。
- **不要提交涉密或客户材料。** 本仓库定位是作为干净、无数据的产品发布；你真实的轨道以本地的、
  被 gitignore 的数据形式存在。
- 对于涉密文件（特权通信、客户卷宗、并购材料），**录入前先确认授权**——把宿主模型当作外部服务对待。

被录入的来源文本一律按**数据，而非指令**处理：文档或网页里嵌入的祈使句是要被分析的内容，绝不是
要被执行的命令。

## 关于 FSRS 的说明

引擎用纯标准库 Python（零依赖）实现了 **FSRS-6** 间隔复习。它经过**行为验证**——由测试锁定其
排程行为（打分顺序、到期日期单调性、新卡片初始化）。与参考 FSRS 实现的精确*数值对齐*被刻意
**延后**：MVP 的目标是正确、可预测、有良好测试覆盖的行为，而不是逐位复刻参考常数。

## 路线图

- **`exam` 与 `applied` 模式**——在 MVP 的 `domain` 模式之上扩展（主干设计已为它们预留了无需返工的接缝）。
- **MCP 服务器**——把内核接口封装为 MCP 的 tools / prompts / resources，让其他宿主（及其他 Claude 界面）
  无需重写即可接入。
- **Obsidian 配套**——基础的一体化用法现在就能用（见上文「在 Obsidian 里用」）；更深的配套
  （在 Obsidian 内显示到期卡片数 / `next_action`、FSRS 状态双向同步）是自然的下一步。

## 致谢

- `methods/learning-science.md` 的教学法改编自 [Matt Pocock 的 `teach` skill](https://github.com/mattpocock/skills)
  （MIT，© 2026 Matt Pocock）——按 learn-everything 的 track/card/FSRS 模型重写。
- FSRS 排程遵循 [open-spaced-repetition/py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
  （FSRS-6）；卡片兼容 [obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition)。

## 许可证

MIT——见 [LICENSE](LICENSE)。
