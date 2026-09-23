# Stage C.V1H：单层四分之一波减反膜教学原型

## 范围

本阶段只为 `quarter_wave_single_layer` 增加本科教学原型，不推广至 `bragg_reflector`、`fp_filter` 或 `tamm_phase_bundle`。

教学内容独立保存在：

```text
web3d/public/teaching/quarter_wave_single_layer.json
```

正式物理结果仍来自：

```text
web3d/public/results/quarter_wave_single_layer.json
```

## 两种模式

- 自由探索：默认模式，原有波长、偏振、相机、动画和膜层交互不受限制。
- 引导学习：用户主动进入，五个步骤分别绑定膜层选择、550 nm、650 nm、TM 偏振和小结题。

用户可随时退出引导，不存在强制首次向导。

## 内容分层

- 默认层：问题说明、学习目标、重点观察对象和实时正式结果。
- 进阶层：光学相位厚度、无损能量关系、常见误区和模型边界。
- 工程层预留在教学契约受众声明中，本原型不新增容差或导出功能。

公式使用原生折叠区，默认关闭。

## 正式数据校正

当前正式 JSON 的入射角为 45°，因此原型没有照搬正入射下 TE/TM 相同的结论：

- 550 nm：TE `R=0.040048`，TM `R=0.001356`；
- 650 nm：TE `R=0.047890`，TM `R=0.002413`；
- 正式 TE 最低反射点约为 472 nm，而不是 550 nm。

页面将 550 nm 称为名义设计参考点，不改写正式曲线。

## 语义边界

- R/T/A 明确标记为 Python TMM 正式结果。
- 正弦波、视觉厚度、方向箭头和偏振方向明确标记为教学示意。
- 不把动态正弦线称为定量空间电场。
- 未提供实时重新计算能力，因此没有开放膜厚修改。

## 自动验证

- 教学契约与正式 JSON 的 case_id、入射角、膜厚和 550 nm 数值一致；
- 五个步骤均声明正式证据字段；
- 引导操作实际改变现有 Three.js 案例状态；
- 默认自由探索、引导可退出、公式默认折叠；
- Renderer 仍为 1，控制台无错误。

浏览器证据：

- `docs/visualization/runtime/stage_cv1h/quarter_wave_free.png`
- `docs/visualization/runtime/stage_cv1h/quarter_wave_guided.png`
