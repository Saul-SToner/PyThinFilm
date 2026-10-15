# 40 例动画资料索引

`video_materials/all_cases_v1/` 含 40 段独立无音轨视频，每段 6 秒、1280×720、15 fps。`public/` 有 App 公开的 22 例，`archive/` 有默认不公开的 18 例。`40_cases_review_240s.mp4` 是按目录顺序串联的四分钟复核长片，不是已完成配音与教学讲解的参赛成片。

画面中的“动画”是沿原始横坐标逐点揭示计算或保存结果，**不表示物理时间演化**。所有来源、显示曲线、点数、结果哈希和本次参数在 `case_video_manifest.json` 中逐项记录。

| 范围 | 来源 | 表达边界 |
| --- | --- | --- |
| 17 个公开薄膜教学基线 | 渲染时重新调用 tmmcore | 使用默认参数，只展示本次基线计算；不是动态扫膜厚。 |
| `fp_single_halfwave` | 渲染时调用 PyThinFilm 求解器 | 与当前 App 对该案例的路由一致，不误标为 tmmcore。 |
| `guided_grating_emt` | 渲染时调用 RCWA | 使用 1.45–1.65 µm、3 谐波；本组参数未显示尖锐共振，不据此宣称已验证导模耦合。 |
| 3 个公开 Tamm 教学实验 | 渲染时调用 GeneralTmm | 当前平面 Ag/DBR 教学模型；偏振反射片显式设 β=0.30，不等同历史 COMSOL 结构。 |
| 18 个归档工程/研究案例 | 原仓库保存的结果或外部证据 | 只作结果回放，保留归档标记、证据状态与限制；不代表本次重新求解或 App 已重新开放。 |

少于 11 个点的证据表以离散点呈现；横坐标恒定的 Tamm 窗口束直接逐行呈现原表，不拟合趋势。减反类 R 图采用局部纵轴，分束同时呈现 R/T，F-P 使用 T；不同单位的指标不叠放同一纵轴。PDRC 的波长单位从 nm 转为 µm，数值未改动。

重建全部视频：

```powershell
& "Frontend/V3/.venv/Scripts/python.exe" tools/video/render_case_library.py --ffmpeg "C:\path\to\full-ffmpeg.exe"
```

中断后加 `--resume`。只刷新指定案例：`--resume --refresh-case-id neutral_beamsplitter`。临时检查单例：`--output video_materials/all_cases_qa --case-id fp_filter`。

参赛正式视频应从公开案例中选取能回答教学问题的镜头，增加预测、观察停顿、物理解释与模型边界；归档案例仅作为补充资料，不能仅凭 40 例复核长片暗示所有工程目标已经完成。
