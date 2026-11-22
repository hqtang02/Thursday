# Code Review Log

记录本项目的 AI 辅助代码审查（GitHub Copilot PR Review）与人工复核过程。

- 仓库：https://github.com/hqtang02/Thursday
- 分支：`thq_test` → `main`
- PR 链接：（请补充，例：https://github.com/hqtang02/Thursday/pull/1）

---

## Round 1 · 2026-11-22（commit `94f0933`）

### AI 审查（GitHub Copilot Review）

> No actionable findings. The added workflow is valid, installs the declared dependencies, runs the intended `test_water_engine.py` suite, and the PR's GitHub Actions run completed successfully.

结论：AI 未发现问题。

### 人工复核——发现 AI 未捕获的问题

1. **CI 测试范围过窄**：`tests.yml` 只运行 `test_water_engine.py`，未运行当前应用的 `test_rainwater.py` 与 `test_recommendation.py`。AI 审查确认"运行的是预期的测试套件"，但未识别测试覆盖范围与实际业务代码不匹配。
2. **默认场景不含灵活任务**：默认勾选的 Bathroom + Garden 均为固定任务，智能调度不会产出优化建议，核心功能无法开箱演示。
3. **表单边界风险**：Initial Storage / Minimum Reserve 的 `max_value` 联动 Tank Capacity，容量调小后已输入的值可能越界报错。
4. **结果缺少参数标注**：结果区未展示计算所用的水箱参数与各场景用水量，用户无法核对结果对应的输入。
5. **文档与依赖不一致**：README 描述的功能与实际应用界面不符；`requirements.txt` 包含未使用的 folium，且缺少实际依赖 streamlit-js-eval。

### 处理：全部采纳并修复（commit `46a4b20`）

- `main.py`：默认场景加入 Laundry（灵活任务）；储水/保留量改为提交时校验并给出明确错误提示；结果区新增参数与用水量标注。
- `tests.yml`：CI 改为 `pytest -q` 运行全部测试。
- `requirements.txt` / `WebClick.bat`：移除 folium，补充 streamlit-js-eval。
- `README.md`：重写为与实际应用 Rainwater Smart Planner 一致。
- 本地回归验证：`pytest -q` 45 个用例全部通过；Streamlit 应用启动健康检查通过。

### 经验记录

AI 代码审查擅长发现语法、配置与安全类问题，但对"测试范围是否覆盖当前业务代码"这类需要项目上下文的问题可能漏判。AI 审查结论需配合人工复核使用。

---

## Round 2 · 2026-11-22（commit `26d9877`，修复后复审）

### AI 审查（GitHub Copilot Review）

> No actionable findings. The workflow is valid, installs the declared pytest dependency, targets Python 3.12, and the pull-request run completed successfully.

### 验证结果

- CI 在 PR 上自动触发，`pytest -q` 全量测试通过 ✅
- 修复后再次审查无新增问题，Round 1 发现的问题全部闭环 ✅

---

## 附：证据截图清单

| 文件 | 内容 |
| --- | --- |
| `screenshots/pr_overview.png` | PR 页面概览（标题、分支、文件变更数） |
| `screenshots/copilot_review_1.png` | Round 1 Copilot 审查结论 |
| `screenshots/copilot_review_2.png` | Round 2 Copilot 审查结论 |
| `screenshots/ci_passed.png` | CI 全量测试通过（绿色勾） |
