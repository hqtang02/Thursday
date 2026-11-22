# Code Review Log

记录 SmartWater Optimizer 的 AI 辅助代码审查（GitHub Copilot PR Review）与人工复核过程。

- 仓库：https://github.com/hqtang02/Thursday
- PR #1：`ctt_test` → `main`
- PR #2：`fix/pr1-copilot-findings` → `main`（PR #1 内容 + 审查修复，为超集）

---

## Round 1 · 2026-11-22 · PR #1（AI 审查：GitHub Copilot）

### AI 发现 4 个可操作问题

1. **High — 北京使用香港水价**：`data/water_config.json` 中北京的 `tariff_key` 为 `hong_kong`，选择北京会按香港阶梯价计算账单。
2. **Medium — 非法阶梯表被接受**：`water_engine.py` `_normalise_brackets` 允许中间档为 null（无上限），后续档位会被静默忽略。
3. **Medium — 畸形 URL 参数可致崩溃**：URL 状态还原只做类型转换不校验取值，`?city=invalid` 写入 session_state 后触发 KeyError。
4. **Medium — drought_mode 无实际效果**：参数只校验并原样返回，未参与计算，但界面宣称"节省目标已自动增加 10% 安全邊際"。

### 人工复核——4 条全部复现确认属实

- 配置文件中 `cities.beijing.tariff_key == "hong_kong"`，而 `tariffs` 表无北京水价；
- 中间档为 null 的阶梯表确实能通过校验；
- `?city=invalid` 会在结果页 `cities[city_key]` 处抛 KeyError；
- 引擎中 `effective_target = target`，drought_mode 全程未参与计算，且既有测试固化了这一行为。

### 处理：全部修复（commit `f4c8b0b`）

1. 城市选择器只列出拥有本地水价表的城市，北京不再可选（其降水数据保留，干旱预警引擎与测试不受影响）；
2. `_normalise_brackets` 拒绝中间档为 null 的阶梯表并给出明确报错；
3. URL 状态还原增加取值校验（城市 / 视图 / 语言 / 月份 / 人数 / 用水量），非法值静默忽略；
4. drought_mode 启用时 `effective_target = target × 1.1`，与界面宣称一致；更新对应测试预期。

测试：更新 drought 用例（目标 20 → 22），新增中间档 null 拒绝用例；**46 个测试全部通过**。

---

## Round 2 · 2026-11-22 · PR #2（AI 复审：GitHub Copilot）

### AI 结论

> PR 2 is the superset and should be preferred; PR 1 contains overlapping changes. Both CI suites pass: PR 1 — 45 tests, PR 2 — 46 tests.

采纳建议：合并 PR #2，关闭 PR #1。

### AI 新发现 1 个问题

5. **整数 URL 参数被截断而非拒绝**：`int(float(raw))` 会把 `?people=2.9` 解析为 2、`?month=1.9` 解析为 1，应严格要求整数语法。

### 人工复核与处理

属实：截断行为会让畸形参数产生看似合法的状态。修复为 `int(raw)` 严格解析，非法值抛出 ValueError 后由外层捕获静默忽略（commit `b09a4a9`）。46 个测试全部通过。

---

## Round 3 · 合并前最终复审（待补充）

PR #2 合并前进行最后一轮 Copilot 复审，确认 Round 1–2 的全部问题闭环。

---

## 经验总结

- AI 审查（Copilot Review）能有效发现数据一致性（北京水价）、输入校验（URL 参数、null 档位）与功能不符宣称（drought_mode）等真实缺陷；
- 也有漏判的情况（如 CI 测试范围与实际业务代码不匹配需人工复核），AI 结论应配合人工验证使用；
- 每一轮"AI 审查 → 人工复现 → 修复 → 回归测试 → 复审"都留痕，形成完整闭环。

## 附：证据截图清单

| 文件 | 内容 |
| --- | --- |
| `screenshots/pr2_copilot_review_1.png` | Round 1：Copilot 在 PR #1 发现 4 个问题 |
| `screenshots/pr2_copilot_review_2.png` | Round 2：Copilot 复审结论与新发现 |
| `screenshots/pr2_ci_passed.png` | PR #2 CI 通过（46 个测试） |
