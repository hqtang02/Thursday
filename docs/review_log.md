# Code Review Log

记录本项目的 AI 辅助代码审查（GitHub Copilot PR Review）与人工复核过程。

- 仓库：https://github.com/hqtang02/Thursday
- 本文件分两部分：Part 1 为 Rainwater Smart Planner（`thq_test` → `main`），Part 2 为 SmartWater Optimizer（`ctt_test` / `fix/pr1-copilot-findings` → `main`，PR #1 / PR #2）。

---

# Part 1 · Rainwater Smart Planner（thq_test → main）

## Round 1 · 2026-11-22（commit `94f0933`，见 PR 时间线）

### AI 审查（GitHub Copilot Review）

> No actionable findings. The added workflow is valid, installs the declared dependencies, runs the intended `test_water_engine.py` suite, and the PR's GitHub Actions run completed successfully.

结论：AI 未发现问题。

### 人工复核——发现 AI 未捕获的问题

1. **CI 测试范围过窄**：`tests.yml` 只运行 `test_water_engine.py`，未运行当前应用的 `test_rainwater.py` 与 `test_recommendation.py`。AI 审查确认"运行的是预期的测试套件"，但未识别测试覆盖范围与实际业务代码不匹配。
2. **默认场景不含灵活任务**：默认勾选的 Bathroom + Garden 均为固定任务，智能调度不会产出优化建议，核心功能无法开箱演示。
3. **表单边界风险**：Initial Storage / Minimum Reserve 的 `max_value` 联动 Tank Capacity，容量调小后已输入的值可能越界报错。
4. **结果缺少参数标注**：结果区未展示计算所用的水箱参数与各场景用水量，用户无法核对结果对应的输入。
5. **文档与依赖不一致**：README 描述的功能与实际应用界面不符；`requirements.txt` 包含未使用的 folium，且缺少实际依赖 streamlit-js-eval。

### 处理：全部采纳并修复（commit `1b0e15c`）

- `main.py`：默认场景加入 Laundry（灵活任务）；储水/保留量改为提交时校验并给出明确错误提示；结果区新增参数与用水量标注。
- `tests.yml`：CI 改为 `pytest -q` 运行全部测试。
- `requirements.txt` / `WebClick.bat`：移除 folium，补充 streamlit-js-eval。
- `README.md`：重写为与实际应用 Rainwater Smart Planner 一致。
- 本地回归验证：`pytest -q` 全部用例通过；Streamlit 应用启动健康检查通过。

### 经验记录

AI 代码审查擅长发现语法、配置与安全类问题，但对"测试范围是否覆盖当前业务代码"这类需要项目上下文的问题可能漏判。AI 审查结论需配合人工复核使用。

## Round 2 · 2026-11-22（commit `1b0e15c`，修复后复审）

### AI 审查（GitHub Copilot Review）

> No actionable findings. The workflow is valid, installs the declared pytest dependency, targets Python 3.12, and the pull-request run completed successfully.

### 验证结果

- CI 在 PR 上自动触发，`pytest -q` 全量测试通过 ✅
- 修复后再次审查无新增问题，Round 1 发现的问题全部闭环 ✅

---

# Part 2 · SmartWater Optimizer（PR #1：ctt_test → main；PR #2：fix/pr1-copilot-findings → main，为超集）

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

## Round 2 · 2026-11-22 · PR #2（AI 复审：GitHub Copilot）

### AI 结论

> PR 2 is the superset and should be preferred; PR 1 contains overlapping changes. Both CI suites pass: PR 1 — 45 tests, PR 2 — 46 tests.

采纳建议：合并 PR #2，关闭 PR #1。

### AI 新发现 1 个问题

5. **整数 URL 参数被截断而非拒绝**：`int(float(raw))` 会把 `?people=2.9` 解析为 2、`?month=1.9` 解析为 1，应严格要求整数语法。

### 人工复核与处理

属实：截断行为会让畸形参数产生看似合法的状态。修复为 `int(raw)` 严格解析，非法值抛出 ValueError 后由外层捕获静默忽略（commit `b09a4a9`）。46 个测试全部通过。

## Round 3 · 合并后最终复审（待补充）

PR #2 已合并进 `main`；对合并结果进行最后一轮 Copilot 复审，确认 Round 1–2 的全部问题闭环。

---

## 经验总结

- AI 审查（Copilot Review）能有效发现数据一致性（北京水价）、输入校验（URL 参数、null 档位）与功能不符宣称（drought_mode）等真实缺陷；
- 也有漏判的情况（如 CI 测试范围与实际业务代码不匹配需人工复核），AI 结论应配合人工验证使用；
- 每一轮"AI 审查 → 人工复现 → 修复 → 回归测试 → 复审"都留痕，形成完整闭环。

## 附：证据截图清单

| 文件 | 内容 |
| --- | --- |
| `screenshots/pr_overview.png` | PR 页面概览（标题、分支、文件变更数） |
| `screenshots/copilot_review_1.png` | Part 1 Round 1 Copilot 审查结论 |
| `screenshots/copilot_review_2.png` | Part 1 Round 2 Copilot 审查结论 |
| `screenshots/ci_passed.png` | CI 全量测试通过（绿色勾） |
| `screenshots/pr2_copilot_review_1.png` | Part 2 Round 1：Copilot 在 PR #1 发现 4 个问题 |
| `screenshots/pr2_copilot_review_2.png` | Part 2 Round 2：Copilot 复审结论与新发现 |
| `screenshots/pr2_ci_passed.png` | PR #2 CI 通过（46 个测试） |
