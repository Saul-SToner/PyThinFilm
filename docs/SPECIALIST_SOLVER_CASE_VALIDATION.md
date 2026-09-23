# 专用求解器案例验证

## 路由

| 案例 | 最终结果来源 | 参数来源 |
|---|---|---|
| `guided_grating_emt` | RCWA | 前端光栅参数 |
| 7 个 `tamm_*` 案例 | GeneralTmm | `tamm_phase_bundle.json` 的 Ag + (HL)3H 八层结构 |
| `pdrc_cooling_bundle` | WPTherml | `pdrc_cooling_bundle.json` 的 SiO2/TiO2/SiO2/TiO2/SiO2/Ag 六层结构 |
| 4 个 `absorbing_*` 案例 | 正式 COMSOL 证据结果 | evidence JSON；原始数据未提供可重建的材料与厚度结构 |

## 前端规则

专用求解器案例只显示最终 R/T/A（PDRC 中 A 同时代表发射率）曲线。不会同时显示 EMT、TMM 近似或占位对照；吸收表面案例读取正式证据结果，不伪造 WPTherml 膜系。

## 验证

- RCWA API：R/T/A 与能量守恒字段可用。
- GeneralTmm：7 个 Tamm 案例全部使用八层材料结构并返回光谱。
- WPTherml：PDRC 使用六层真实材料结构并返回光谱。
- 吸收表面：4 个案例均能读取正式证据摘要、曲线或表格。
- V3 后端测试：34 passed。
- 前端 TypeScript 检查和生产构建：通过。
