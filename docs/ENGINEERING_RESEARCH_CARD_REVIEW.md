# 工程应用与研究拓展卡片审阅

范围：5 个工程应用、16 个研究拓展。逐例读取案例目录、详情、摘要、边界和曲线；本轮是数据语义与展示审查，不是重新运行全部原始 COMSOL 工程。

## 工程应用

| 案例 | 发现及处理 |
|---|---|
| 太阳电池三层膜 | 导出平均 R=38.68%，裸硅 R=30.86%；反射增加约 7.82 个百分点，不能宣称减反成功。移除效率提升标签，明确常数折射率模型、不含电学转换效率 |
| WDM | 峰值约 1550.10 nm，FWHM 约 11.82 nm；没有完整 DWDM 通道规范与串扰验证。补充单片滤光教学边界 |
| 激光镜 | R 约 99.9233% 支持特定模型的高反表述，不能证明损伤阈值或腔性能。纠正物理模型名称 |
| 手机镀膜 | 三层平均 R=15.50%，单层约 0.943%；反射增加约 14.56 个百分点。移除负数“改善率”，明确当前设计未优于基准 |
| Low-E | 固定 WO3/NiO/Ag 状态，不能宣称电致变色切换或热平衡。纠正模型与说明 |

## 研究拓展

| 案例 | 审阅边界 |
|---|---|
| mat_library_demo | 仅 MgF2/SiO2 代表，非整个库的同时分析 |
| tamm_interface_priority | 历史候选筛选通过数为零；当前 GeneralTmm 实验不能替代历史证据 |
| tamm_phase_bundle | 历史固定参考面验证与当前 Ag/DBR 实验分开解释 |
| tamm_phase_candidates | 历史严格通过数为零，不能宣布找到界面态 |
| tamm_phase_focus | 历史三个厚度组与当前平面实验不同；吸收不直接等于局域场 |
| tamm_reflection_phase_screen | 历史相位筛选未通过，当前实验不复现端结构 |
| tamm_interface_window_bundle | 历史缺三个输入，单 y 截面非二维场；与当前实验分开 |
| tamm_interface_window_scan | 历史窗口统计与当前 β 扫描不是同一对象 |
| pdrc_cooling_bundle | 历史有效常数近似与当前 WPTherml 分开；未验证净制冷 |
| absorbing_baseline_template | 已绑定 CSV，却显示等待绑定；卡片与边界已纠正 |
| absorbing_surface_bundle | COMSOL 粗糙结构证据，不是可重建逐层 TMM |
| absorbing_surface_gain | 增益仅针对两个给定输入 |
| absorbing_surface_gain_trend | 六个离散点不能外推连续严格单调 |
| rugate_80layer_table | 离散近似，非连续精确解或自动 COMSOL 验证 |
| advanced_ar_bundle | 五项对照汇总，不是一个复杂镜头模型 |
| porous_double_ar_topic_bundle | 单谱验证不等于多参数容差验收 |

所有案例新增/修订的适用范围通过默认折叠卡片显示。保留原始证据与光谱，不修改其物理数值；显示层用显式基准差值替换误导性提升标签。

验证：前端类型检查通过，案例目录/验收接口 9 项测试通过。尚待逐卡片视觉复验、原始工程来源独立重算，以及统一全部历史摘要的中文字段与单位；不据此宣布工程/研究模型全部验收通过。
