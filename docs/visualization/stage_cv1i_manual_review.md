# Stage C.V1I 人工检查表

## Bragg reflector

打开 `/apps/bragg-reflector/`：

- 498 nm TE 应显示高反射，700 nm TE 应回到低反射；
- TM 498 nm 的正式反射率应低于 TE；
- 页面应说明当前为 45° 且膜厚未做斜入射补偿。

## F-P filter

打开 `/apps/fp-filter/`：

- 第 7 层应为中央 C 腔；
- TE 484 nm 应标记为正式缺陷模；
- TE 546 nm 应为高反阻带对照；
- 页面应区分缺陷模与 664/644 nm 阻带外全谱最大透射。

## Tamm phase bundle

打开 `/apps/tamm-phase-bundle/`：

- 第一层应为 30 nm Ag，参考界面为 Ag/H1；
- 634.2 nm 应显示 R/T/A 均非零；
- 页面应说明正式场数据与外部正弦示意不是同一对象；
- 最终结论必须保持“有损泄漏候选”，不能写成严格本征态。

## 共同行为

- 默认自由探索；
- 引导学习可进入、退出；
- 每一步必须实际改变当前案例控件；
- 公式默认折叠；
- Renderer 始终为 1；
- 控制台无错误。

## 最终视觉验收记录

验收日期：2026-08-02

验收环境：真实浏览器，1280 × 720、DPR 1.5。该视口小于目标检查尺寸 1366 × 768。

### 四案例结论

- `quarter_wave_single_layer`：通过。单膜层可见；550 nm 保持名义参考点语义，约 472 nm 的正式 TE 反射谷与 45° 下 TE/TM 分裂均可发现。
- `bragg_reflector`：通过。H/L 周期、阻带内外对照及 TE/TM 差异清楚，多层结构仍可阅读。
- `fp_filter`：通过。第 7 层中央缺陷腔可定位，缺陷透射峰与阻带外全谱最大透射点在引导内容中明确区分。
- `tamm_phase_bundle`：通过。Ag/H1 界面和 `PHASE_MATCHED_LEAKY_CANDIDATE` 状态清楚；相位/光谱证据与外部正弦教学示意保持语义边界。

### 共同视觉结果

- 首屏案例名称、核心结构和“自由探索”模式可见；
- 正式 R/T/A 面板与“教学示意”标识在位置和视觉层级上分离；
- 四例引导步骤均保持单一主要任务，底部导航在窄视口仍可见；
- 引导抽屉完整位于视口内，不触发页面级横向或纵向溢出；
- 波长、偏振及 R/T/A 在引导打开时仍可见；
- 公式默认折叠；展开两个公式后只产生抽屉内部少量滚动，不影响页面或 Canvas；
- 动态波、方向箭头和膜层结构没有形成阻断性遮挡；
- 选中层高亮可辨，并保留原材料颜色；
- 正弦波“不代表定量空间电场”的常驻提示可见；
- 进入、退出和重新进入引导无相机突变，Canvas 与 Renderer 不重复创建；
- 四案例导航期间控制台无错误。

### 已知非阻断问题

- 引导抽屉会覆盖场景中央的一部分，但不挤压布局；左侧结构、右侧正式结果和退出入口仍可操作。
- 多层案例的完整膜层列表需要在右侧面板内滚动；当前波长和正式功率结果无需滚动即可读取。
- 选中高亮采用克制的描边与色调变化，适合当前学术风格，但后续视觉阶段仍可继续优化对比度。

## 阶段判定

```text
Stage C.V1I teaching logic       = PASSED
Formal-result binding            = PASSED
Zero-power wave suppression      = PASSED
Case-specific pedagogy           = PASSED
Tamm evidence boundary           = PASSED
Guide lifecycle                  = PASSED
Automated regression             = PASSED
Manual visual acceptance         = PASSED
Final freeze                     = READY
```

本次冻结不包含 Three.js 材料配色、灯光与相机、整体页面风格、后续工作区架构、热力图或 Python API。
