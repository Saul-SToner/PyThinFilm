# Optiland 系统动画资料

`video_materials/optiland_system_v1/` 包含三段 12 秒、1280×720、20 fps 的无配音原片，另有 36 秒串联预览。所有参数与逐状态数值见 `optiland_system_manifest.json`；脚本 `tools/video/render_optiland_system_clips.py` 可重算。

| 原片 | 实际变化 | 固定参照与解释边界 |
| --- | --- | --- |
| `01_lens_energy_ghost.mp4` | MgF2 0/80/90/99.6/110/120/130 nm；Optiland 顺序追迹的平均出射光线权重及匹配几何 NSQ 鬼像接收占比 | 相同 N-BK7 单透镜、焦面、550 nm；前半为原生 2D，后半为同一固定几何的原生 3D。鬼像固定随机种子 2026、每状态 10,000 条射线；“差异 > 3 倍合并标准误”仅比较鬼像接收功率，不是普遍性能保证。Spot/MTF/PSF 未宣称随膜改变。 |
| `02_mirror_reflection.mp4` | TiO2/SiO2 从 1 到 6 周期；真实 NSQ 镜面反射探测器功率与膜系 R 一致 | 45°、550 nm、入射 1 W；镜面是单个不透明平面元件，`1-R` 为“未反射损失”，不等同于纯吸收或激光腔反馈。路径方向不随周期伪造改变。 |
| `03_splitter_two_branches.mp4` | 固定四层膜中 TiO2 两层同厚度从 30 到 130 nm；同一次 NSQ 追迹的反射与透射接收功率 | 45°、550 nm、入射 1 W；空气中零厚度等效分光面，不含实际基片厚度和背面反射。两探测器 R/T 功率预算在各状态数值闭合。 |

单镜与分束每状态各追迹 4,096 条射线、固定种子；探测功率和膜系 R/T 绝对误差均小于 `1e-8 W`，方向误差与损耗修正预算残差小于 `1e-8`。镜头片的鬼像只适用于当前透明单透镜教学基线，没有扩展为多片复杂镜头或任意膜材的结论。

`PyThinFilm_5_40_Optiland_326s.mp4` 按“五段薄膜物理 → 40 例目录复核 → 三段系统应用”的顺序合成，仅用于审阅素材。它不等同于带配音、推理停顿和证据解释的正式参赛视频。

重建：

```powershell
& "Frontend/V3/.venv/Scripts/python.exe" tools/video/render_optiland_system_clips.py --ffmpeg "C:\path\to\full-ffmpeg.exe"
```
