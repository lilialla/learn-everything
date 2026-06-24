# learn skill — 使用反馈与待优化记录

> 记录真实使用中暴露的问题，作为后续优化 SKILL.md / 流程的素材。

## 2026-06-24 · RAG 文章学习首测

### 问题 1（关键）：跳过了「原文落地 + 清洗排版」这一步，直接开始讲

- **现象**：用户粘贴一篇 RAG 长文让我学。我做了 create-track → MISSION → map → 直接开始教学（模块 1）。
  但**没有先把原文清洗排版成一份干净的本地 MD**。
- **用户期望（核心学习节奏）**：「看原文 + 对话」。即应先把文章存成本地 MD、去掉无关内容（导航/广告/评论/推广）、
  排好版，让用户在 Obsidian 里**分屏**：左看原文、右对话。否则用户没有原文可对照，纯在对话框里学非常难受、
  全文格式也难读。
- **根因**：当前 SKILL.md 的 INGEST 流程里，Step 1（SECURITY）只要求把粘贴文本「当 DATA 包起来推理」，
  Step 7 PERSIST 才在**批准后**把 source 存进 notes。**没有一个「在教学开始前，先把原文清洗成可阅读 MD 落地」
  的强制前置步骤**。导致 AI 把原文留在对话历史里，而不是生成可分屏阅读的产物。
- **修复方向（建议写进 SKILL.md）**：
  - 在 INGEST 新增前置步骤（Step 1.5 或并入 Step 3 FRAME 之前）：
    **「READER ARTIFACT — 落地可读原文」**：当学习素材是用户粘贴/抓取的长文时，先清洗（去 UI/广告/评论/推广噪音、
    保留正文+代码+参考链接）、排版成 `tracks/<id>/notes/<date>-<slug>-原文.md`，并提示用户分屏打开，
    **再开始诊断/教学**。
  - 这一步应「默认执行、无需用户提醒」，而不是等用户指出。
  - 与现有 tutor-style read-along + Obsidian split-screen 的产品定位一致（见 MEMORY: learn-everything-tutor-ux）。

### 问题 2（次要）：未把「先落地文件再分块/对话」作为默认习惯

- 用户历史偏好（profile / ep692）已多次强调：**先把内容保存为本地文件再处理，而不是直接塞进对话框**。
  这点应在 learn skill 的 INGEST 里固化为默认行为，不依赖每次提醒。

### 待办

- [x] 把「READER ARTIFACT 落地原文」步骤补进 SKILL.md 的 INGEST 流程 —— 已加入 BEAT 1（默认执行、无需提醒）
- [ ] 考虑在 STATUS/RESUME 时，如果某 track 有 notes 原文，提示用户分屏打开（次要）
- [ ] 评估是否需要一个专门的清洗脚本（类似 legal-text-format）供 learn 复用，保证排版一致（次要）

## 2026-06-24 · 第二批（机制层修复）

### 问题 3（关键）：只记「教了什么」，不记「学习者答了什么、错在哪」

- **现象**：实测时笔记只写了讲解内容，用户的两个卡点（向量不可逆、把检索 R 和生成 G 压成一步）
  没被自动记录，是用户追问才补的。
- **根因**：教学循环没有把「捕捉学习者的回答与误解」当作机制步骤；learner-model 的卡点推断是静默的、
  从不持久化。
- **已修**：
  - `methods/tutor.md` 每概念循环新增 **Capture 步**（强制记录学习者的复述 + 具体误解）。
  - `methods/learner-model.md` 持久化从「可选」改为机制：确认的卡点写入 `CONTEXT.md` 的「Known sticking points」，
    被纠正的误解写一条 dated `learning-records/NNNN-slug.md`。
  - `SKILL.md` BEAT 2 + 会话关闭：明确「捕捉学习者而非只记教学」，并写 learning-records 细节层。

### 机制确认：这个文件本身就是「反馈记录机制」

- `SKILL.md` Reminders 已固化：真实使用暴露的 skill 缺陷 → 追加到本文件（问题 → 根因 → 修复方向）；
  优化 skill 时先读本文件。两类记忆都已成机制：①学习者的路径（notes/CONTEXT/learning-records）；
  ②skill 自身的缺陷（本 FEEDBACK.md）。
