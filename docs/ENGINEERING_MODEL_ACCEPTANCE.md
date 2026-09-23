# 工程模型验收报告

日期：2026-09-20。范围：40 个案例绑定的全部 34 个 Optiland 模板，包括当前未开放 App 转入的模板。

后续两步修复与有限基线复验见 `OPTILAND_BASELINE_ACCEPTANCE.md`。下文是修复前的完整审查快照，不能将已修复的波长、视场问题当作当前状态；其余系统族仍未整体通过工程验收。

**总判定：工程验收不通过。** 34 个模板可构建并完成基准追迹，但不能等同于已实现其名称所承诺的工程系统。当前可保留为教学原型，不应作为实际镜头、激光腔或热管理系统的定量验收结果。

## 实测方法与边界

运行 `../optiland/.venv/Scripts/python.exe experiments/audit_engineering_models.py`。所有模板统一使用 Air/N-BK7，比较裸表面与 100 nm MgF2 镀膜，工作波长 550 nm、32 点均匀采样、归一化轴上视场。检查构建、出射权重有限性及 [0,1] 范围，并比较几何指纹。

- 34/34 完成以上检查；仅代表基准追迹数值可用。
- 34 个名称对应 10 种几何指纹（包括孔径和配置视场）。
- 输出：`Frontend/V3/backend/outputs/engineering_model_audit.json`，逐模板列出关联案例、面数、镀膜面数、视场、几何指纹、裸表面/镀膜权重。
- 不是全波段、全视场、制造容差或逐图视觉验收；光线权重落在 [0,1] 内也不等同于完成系统 R+T+A 能量守恒验证。
- 前一次逐案例运行结果及限制见 `CASE_RUNTIME_REVIEW.md`。

## 全部模板分类结论

| 模板（覆盖全部 34 个） | 实际实现 | 工程验收结论及缺口 |
|---|---|---|
| single_lens_imaging | 单透镜，前面实膜、后面裸界面 | 教学基线可运行；欠缺焦面、视场、像质和通量独立基准 |
| camera_lens_coverglass、wide_angle_window | 与单透镜相同 | 不通过：没有独立盖板/宽角窗口结构 |
| multi_element_imaging、photographic_lens、dispersive_lens | 共用两片同材质透镜 | 仅教学原型；未验证焦面、多材料色差、多表面镀膜收益 |
| phone_camera_module、complex_camera_lens | 各自三片同材质透镜，仅首面使用当前膜堆 | 仅教学原型；不是优化后的手机/复杂镜头设计，缺少像质目标与多表面镀膜基准 |
| wide_angle_multi_element、wide_field_camera | 两片透镜、配置 18° 视场 | 不通过：实际 Spot/PSF/MTF 和能量追迹只采轴上，未测配置边缘视场 |
| dual_band_imager | 两片透镜，单工作波长 | 不通过：没有双波段联合验证 |
| dual_path_beamsplitter | 普通两片透镜，单条顺序透射路径 | 不通过：缺反射支路、双探测器和分光比验证 |
| sensor_prefilter | 镀膜平行窗口及接收面 | 可作为滤光窗口教学原型；仍需实际工作波段、光谱采样和探测器积分验证 |
| spectral_camera、multispectral_imager、dual_channel_spectral_imager、spectrometer、high_resolution_spectrometer、wdm_receiver | 共用平行窗口及接收面 | 不通过：没有成像/分光或通道结构；缺通带采样、通道串扰和目标波段响应 |
| solar_cell_receiver、low_e_window | 同一平行窗口 | 不通过：缺太阳光谱加权、器件响应、可见/红外联合评价；不能由可见光通量直接推出效率或隔热能力 |
| folded_reflector、laser_expander、dbr_laser_cavity | 平面透射界面序列 | 不通过：没有反射模式与真实折返、扩束或腔往返传播，当前透射通光量不是反射效率 |
| phase_interferometer、polarized_phase_screen、prism_coupled_tamm、prism_coupled_tamm_scan、prism_coupled_tamm_window、tamm_absorption_probe | 共用平面顺序界面，配置 25° 视场 | 不通过：没有棱镜几何、干涉双臂或相位读出；GeneralTmm 专用结果不能自动视为 Optiland 系统验证 |
| radiative_cooling_emitter、photothermal_receiver、photothermal_parameter_scan | 单平面窗口 | 不通过：缺温度、发射、太阳/大气光谱和热平衡；WPTherml 结果另行评价 |
| grating_waveguide_coupler | 与热模型相同的单平面窗口 | 不通过：没有光栅、衍射级或波导；RCWA 专用计算不等于此 Optiland 模板成立 |

## 公共阻断项（源码证据）

1. `experiments/optiland_ar_comparison.py::_trace_snapshot` 固定使用 `DESIGN_WAVELENGTH_NM`（550 nm）。实时脚本调用时未传当前波长。1064 nm/通信波段的能量指标可能实际算在 550 nm。
2. 同文件 `_spot_data`、`_psf_and_mtf` 固定视场 `(0,0)`；模板声明视场不等于这些指标覆盖该视场。
3. `experiments/optiland_draft_render.py::run_render` 强制光谱网格为共同可见范围、10 nm 步长。不能验收近红外 WDM/激光，也可能漏掉 F-P 窄峰。
4. 同函数以可见光网格最近点 R/T 驱动实际探针波长的 NSQ。探针落在可见范围外时，R/T 与声明波长不一致。
5. `_trace_nsq_ghost` 使用独立标准单镜片场景，不跟随顺序模型镜片几何。当前鬼像结果不能标为手机/复杂镜头的鬼像性能。
6. `_plot_energy_comparison` 是入射、单面法向透射、像面三个检查点，不是逐表面能量预算；`throughput_gain` 是差值，不是相对增益比值。
7. `thinfilm/optiland_integration.py::build_system` 无反射/衍射/分支建模参数。未知模板还会回退单透镜，容易以成功图像掩盖未实现模型。
8. 多数模板只在首面使用当前实膜；材料来自自由设计基底，Air 基底可能让所谓透镜没有折射能力。真实材料替换也不保证复现常数 n/EMT 膜系。
9. 工程案例有描述元数据但当前禁止转入自由设计；应验收实际可达入口，不能以模板存在代替 App 接通。

## 修复优先级与复验标准

1. 先统一工作波长、视场、扫描区间和图像结果来源；禁止未知模板静默回退。使用 550/1064/1550 nm 和轴上/边缘视场验证确实传入求解器。
2. 成像与滤光窗口先形成可验收基线：明确焦面、孔径、材料和镀膜面；分别对比未镀膜/镀膜，验证能量预算、角度响应及窄峰采样收敛。系统鬼像必须使用对应几何。
3. 独立完成反射镜与分光器：真实反射光线/双支路，检查方向、出口功率及 R/T/A 预算，再讨论激光腔或扩束。
4. WDM、Low-E、光伏使用各自工作光谱与探测器/加权函数；热辐射、Tamm、光栅保留各自专用求解器边界，未建立耦合前不声明 Optiland 已实现。

本轮仅验收、记录证据和建立可重复检查脚本，未为了通过验收而修改物理模型或放宽阈值。
