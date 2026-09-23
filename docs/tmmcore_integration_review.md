# tmmcore 第二后端接入审阅记录

## 决策

不把 TFStudio 整体并入 PyThinFilm。仅复用其独立 MIT 许可计算库 `tmmcore`，并保持统一设计接口与明确的求解器归属。

## 当前边界

- tmmcore 现在是自由设计工作区的平面多层膜 R/T/A 默认后端。
- 教学主树的 18 个案例现均经过 tmmcore 光谱路径；蛾眼有效渐变层与 Rugate 连续渐变先由 PyThinFilm 按既有规则离散切片，再由 tmmcore 计算，响应标记为 `layer_sliced_approximation`。
- PyThinFilm 负责教学组织、场分布、自动评价、EMT/RCWA 和专用后处理，并保留为显式对照后端。
- 上层通过 `POST /api/designs/simulate` 使用同一份设计数据，不直接操作任何求解器内部模块。
- 当前不批量动态化后22例，不把外部 COMSOL 数据案例改写为内部全波求解。

## 一致性门槛

接入必须通过以下基准，R/T/A 最大绝对误差小于 `1e-10`：

1. 单层减反膜；
2. Bragg 周期膜堆；
3. F-P 缺陷腔；
4. 30° 斜入射有损银膜的 s/p 偏振约定审计。

测试入口：`Frontend/V3/backend/tests/test_tmmcore_consistency.py`。

## 后续门槛

只有在案例参数模型、材料范围、单位、复折射率符号和参考结果均完成逐例审计后，才允许把某个案例的 `solver` 默认值切换为 `tmmcore`。外部数据依赖和特殊求解案例继续保持联合计算或 PyThinFilm 专用路径。
