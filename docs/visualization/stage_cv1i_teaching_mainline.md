# Stage C.V1I：本科教学主线推广

## 范围

在已验收的 `quarter_wave_single_layer` 原型基础上，本阶段完成：

- `bragg_reflector`
- `fp_filter`
- `tamm_phase_bundle`

四个案例形成以下教学主线：

```text
两束相消减反
→ 多界面相长高反
→ DBR 阻带中的缺陷腔谐振
→ 金属/DBR 共同参考相位候选态
```

## 内容独立性

三个新案例分别拥有独立教学契约：

```text
web3d/public/teaching/bragg_reflector.json
web3d/public/teaching/fp_filter.json
web3d/public/teaching/tamm_phase_bundle.json
```

它们共用已验收的面板渲染和控件绑定组件，但不共用问题陈述、观察结论、步骤、证据字段、小结题或模型边界。

## Bragg 案例

- 识别七层 H/L 周期；
- 比较 TE 498 nm 高反峰与 700 nm 阻带外状态；
- 比较 TM 在 45° 下更窄、更低的正式阻带；
- 强调高反来自多界面相长，而不是单层或视觉厚度。

## F-P 案例

- 识别 `(HL)³ C (LH)³` 中央缺陷腔；
- 比较 TE 484 nm 缺陷模和 546 nm 阻带；
- 比较 TM 486 nm 峰及不同线宽/Q；
- 明确阻带外全谱最大 T 不能冒充缺陷模。

## Tamm 案例

- 识别 Ag/H1 共同参考界面；
- 检查 634.2 nm 的 R/T/A；
- 联合共同参考相位残差和正式场局域指标；
- 将结论严格限定为 `PHASE_MATCHED_LEAKY_CANDIDATE`。

## 边界

- 未修改 Python 物理计算或正式结果 JSON。
- 未新增膜厚实时计算。
- 正弦线仍为教学示意，不冒充 F-P 腔场或 Tamm 正式场剖面。
- 公式默认折叠。
- 本阶段没有推广到其他工程应用案例。

## 浏览器证据

- `docs/visualization/runtime/stage_cv1i/bragg_guided.png`
- `docs/visualization/runtime/stage_cv1i/fp_guided.png`
- `docs/visualization/runtime/stage_cv1i/tamm_guided.png`
