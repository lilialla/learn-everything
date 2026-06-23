# learn skill 系统审查 — 发现的问题清单

**审查日期**: 2026-06-24  
**状态**: ✅ 已优化（见下方"解决映射"）  
**类型**: skill 执行流程 / 模式设计 / 严格性

---

## ✅ 解决映射（2026-06-24 优化）

根因：SKILL.md 的 INGEST 本身就把流程编码成 `Map → 直接提卡 → 批准 → 落库`，
**结构上跳过了"诊断 + 对话式教学"**，所以模型照做就是卡片工厂。已改：

| 审计问题 | 修复 |
|---|---|
| 1 跳过 MISSION | 新增确定性门禁 `registry.py ingest-check`（MISSION 是 stub → `ready:false` 硬挡）；INGEST Step 0 强制先跑它 |
| 2 没诊断学习模型 | INGEST 新增 **Step 2 DIAGNOSE**（强制，先问背景/目标/深度，拿到 grasp+goal 才能教）|
| 3 违反 tutor 对话式 | INGEST 新增 **Step 4 对话式教学**；`tutor.md` 加"每概念 Expose→Probe→Adjust→Confirm 循环"+ 顶部禁止"独白结尾甩卡" |
| 4 Step 3 提前落库 | 拆成 **Step 5 提案（小、必要时存文件）→ Step 6 显式批准 → Step 7 才落库**；顶部 FORBIDDEN 块明令"批准前不写盘" |
| 5 没显式选教学法 | Step 3 FRAME 显式声明教学法并可切换 |
| 6 没加载 learning-science | Step 3 顺带说明学习科学"为什么"（learning-science.md）|
| （元）往对话框灌内容 | Ground rule 新增"别 dump 大产物进 chat，存文件再指给用户" |

落地文件：`scripts/registry.py`(ingest-check)、`skills/learn/SKILL.md`(INGEST 重写+禁止块)、
`methods/tutor.md`(对话循环)、`tests/test_registry.py`(门禁测试)。测试 39→40 绿。

---

---

## 问题 1: 跳过 MISSION.md 初始化

**现象**：
- 轨道 `datawhale-llm` 的 MISSION.md 处于 stub 状态（`mission_present: false`）
- 我直接跳到了 INGEST 流程，没有先引导用户填写"为什么学 LLM"

**应该做的**：
- SKILL.md 说"Fill the MISSION"是 CREATE 流程的必要一步
- 如果轨道已 active 但 MISSION 还是 stub，应该在任何教学前**先问用户**
- MISSION 是每个学习决策的基础，不能跳过

**严格性缺失**：
- 我没有检查 MISSION 状态就直接推进，违反了"数据优先"的原则

---

## 问题 2: 没有诊断用户的学习模型

**现象**：
- SKILL.md 说"Always compose `methods/learner-model.md` alongside the track's pedagogy"
- 我完全没有做这一步
- 直接生成卡片时，没有了解：
  - 用户对 RAG 的当前理解水平
  - 用户是否有向量搜索 / AI 背景
  - 用户的学习偏好（概念优先还是问题驱动）

**应该做的**：
- 在 INGEST 之前，**诊断** `grasp` / `misconception` / `load`
- 根据诊断结果选择教学深度和顺序
- 这是"条件化下一个教学步骤"的必要前提

**严格性缺失**：
- 我跳过了人与人之间的**对话诊断**，导致卡片可能不符合用户的学习状态

---

## 问题 3: 违反了 tutor 的"read-along"模式

**现象**：
- SKILL.md 说 tutor 是"read-along teaching"（边读边教）
- 我生成了 20 张卡片的完整清单，直接要求用户"确认"
- 这变成了"快速生成 + 被动确认"，而不是"互动讨论 + 共同理解"

**应该做的**：
- tutor 应该是**对话式的、迭代式的**
- 逐个概念讨论，而不是一次性列出 20 张
- 用户的反馈应该**动态调整**后续内容和卡片设计

**严格性缺失**：
- 我把 tutor 当成了 card factory，违反了这个 pedagogy 的核心精神

---

## 问题 4: INGEST 流程 Step 3 执行不当

**现象**：
- SKILL.md Step 3 说"REQUIRE approval"和"Do not write anything yet"
- 我生成了完整的卡片清单并**已经存到文件**（`ingest-session-20260624-rag-article.md`）
- 这不符合"等待用户确认后再保存"的约定

**应该做的**：
- Step 3 应该只是**提议** — 给出 3-5 个关键概念的逐块讨论计划
- 等用户反馈：理解了吗？要改什么吗？
- **只有**用户明确说"可以了，出卡"，才执行 Step 4（持久化）

**严格性缺失**：
- 我把"提议"和"执行"混在一起，没有真正的确认把关

---

## 问题 5: 没有明确的"教学法选择"

**现象**：
- 轨道的 pedagogy 是 `tutor`（已预设）
- 但我没有显式地向用户说明"我现在用 tutor 模式，这意味着…"
- 也没有问用户是否希望切换到 `socratic` / `feynman` / `active-recall`

**应该做的**：
- 在开始前显式确认：你想用哪种教学法？
- 让用户了解不同模式的区别
- 根据用户选择加载对应的 `methods/<pedagogy>.md`

**严格性缺失**：
- 我默认执行，没有让用户**参与流程选择**

---

## 问题 6: 没有加载 `methods/learning-science.md`

**现象**：
- SKILL.md 说"Also compose `methods/learning-science.md`"
- 这是跨切的"为什么"和**storage strength** 的理论基础
- 我完全没提

**应该做的**：
- 在 INGEST 之前向用户解释：为什么这样分块？为什么这样出卡？
- 这是透明度和可信度的来源

**严格性缺失**：
- 用户不知道 skill 背后的学习科学依据

---

## 核心问题总结

| 问题 | 类型 | 严重性 |
|------|------|--------|
| 跳过 MISSION.md | 流程缺失 | 高 |
| 没有诊断学习模型 | 教学设计缺失 | 高 |
| 违反 tutor 的"对话式"原则 | 模式偏离 | 高 |
| INGEST Step 3 执行错误 | 流程缺失 | 中 |
| 没有显式选择教学法 | 用户代理权 | 中 |
| 没有加载 learning-science | 透明度缺失 | 低 |

---

## 优化方向（待讨论）

1. **在代码 / 模板级别**强制 MISSION.md 检查
2. **设计诊断问卷**自动化用户学习模型推断
3. **改进 INGEST 流程**为严格的对话式（Step 3 不出卡，先讨论）
4. **显式教学法选择**而不是默认执行
5. **加载 learning-science 说明**作为 INGEST 的第 0 步

---

## 下一步

等待用户明确：
- [ ] 这个审查是否准确？
- [ ] 优先修复哪些问题？
- [ ] 对"正常状态"定义有什么补充？
