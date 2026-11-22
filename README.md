# Rainwater Smart Planner

智能雨水收集与七日用水调度器。基于 Open-Meteo 七日降雨预报，模拟屋顶水箱的逐日水量平衡，并在穷举所有合法调度方案后，给出高优先级用水零缺口的智能任务安排。**除天气 API 外无其他外部依赖。**

## 快速开始

```bash
pip install -r requirements.txt
pytest -q
streamlit run main.py
```

Windows 用户也可直接双击 `WebClick.bat`。

> 注意：需要 Streamlit ≥ 1.67（界面使用 `streamlit.components.v2` 自定义组件）。定位与降雨预报需要联网访问 Open-Meteo（免费、无需密钥）。

## 界面功能

- **欢迎首页**：全屏自定义组件，点击进入主界面，无闪动动效。
- **双模式定位**：GPS 浏览器定位（点击后才请求权限）或全球城市搜索（Open-Meteo 地理编码，支持重名城市选择）。
- **七日降雨卡片**：按降水量分级展示无雨 / 小雨 / 中雨 / 大雨动画与毫米数，标注数据获取时间。
- **六场景用水选择**：浴室、厨房、洗衣、花园、车道、客厅，各带基准用水量、优先级与"固定每日 / 灵活单次"属性，Low / Medium / High 三档按 0.6 / 1.0 / 1.5 系数缩放。
- **水箱参数**：集水面积、水箱容量，高级设置含收集效率、初始储水、最低保留水位，非法组合（储水超过容量）会给出明确报错。
- **智能调度结果**：收集 / 分配 / 缺水 / 溢流四指标卡，基线与优化方案对比，七日逐日计划表，水箱存量曲线，收集-分配柱状图，分级文字建议，一键导出 CSV。
- **结果参数标注**：结果区完整展示本次计算所用的位置、水箱参数与各场景用水量，便于核对。

## 项目结构

| 文件 | 职责 |
| --- | --- |
| `rainfall_service.py` | Open-Meteo 城市搜索与未来 7 天降水预报抓取，带输入校验与网络错误处理 |
| `rainwater_engine.py` | 纯 Python 核心引擎：逐日水量平衡模拟与调度穷举优化，不依赖 Streamlit |
| `recommendation_engine.py` | 对比基线与优化方案，生成缺水 / 溢流 / 任务调整建议 |
| `main.py` | Streamlit 单页交互界面，只负责展示与调用引擎 |
| `test_rainwater.py` / `test_recommendation.py` | 核心引擎与建议生成的 pytest 单元测试 |
| `assets/` | 场景卡片图片 |

`water_engine.py`、`data/`、`test_water_engine.py` 为早期迭代（阶梯水费计算器）的遗留代码与测试，仍通过全部测试，保留供参考；更早期的页面实现位于 `archive/`。

## 核心引擎 API

- `run_schedule(rainfall, area, capacity, tasks, schedule, ...)`：按给定调度模拟完整七日，逐日计算收集量、溢流（超出容量）、按优先级分配、缺水与剩余存量。
- `baseline_schedule(tasks)`：基线方案——灵活任务排在允许窗口的最后一天。
- `compare_strategies(rainfall, area, capacity, tasks, ...)`：穷举灵活任务的全部日期组合（上限 50000 种），按字典序评分取最优：① 高优先级任务缺水量 → ② 总缺水量 → ③ 总溢流量 → ④ 调度变动次数。返回基线与优化两套完整模拟结果。
- `generate_recommendations(comparison, dates, tasks)`：由两套方案的差异生成文字建议。

`WaterTask` 字段：`name`、`amount`（升）、`priority`（1 最高）、`flexible`、`earliest_day` / `latest_day`。非法输入（空降雨序列、负面积、效率超出 [0,1]、任务窗口越界、固定任务跨多天等）会主动抛出 `ValueError`。

## 每日水量平衡公式

```
收集量(L) = 降雨(mm) × 集水面积(m²) × 收集效率
溢流(L)   = max(0, 昨日存量 + 收集量 − 水箱容量)
可用水(L) = 当前存量 − 最低保留水位
分配      = 当日任务按 (优先级, 场景顺序) 依次供水，不足部分记为缺水
```

## 说明

降雨数据来自 Open-Meteo 七日预报，用水量基准为演示估算值；背景水位动画反映已选场景数量而非真实储水量。CI 由 GitHub Actions 提供，push 与 PR 时自动运行全部 pytest 用例。
