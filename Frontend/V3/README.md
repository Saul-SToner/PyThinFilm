# PyThinFilm V3 桌面端

V3 同时保留两种工作区：

- **自由膜系设计**：编辑任意膜层、选择真实色散材料、查看 R/T/A 与 Three.js 三维结构。
- **案例库**：完整目录包含 40 例；当前默认公开 22 例（18 个薄膜教学、1 个光栅实验、3 个 Ag/DBR 教学实验），其余 18 例归档。发布范围以 `backend/app/case_release.py` 为准。

案例库不会把研究证据案例伪装成可调参数教学仿真。实时案例显示参数与“开始仿真”；正式结果/证据案例显示已有曲线、膜层、指标、表格和适用范围。非教学 Runner 不计入 40 个物理案例。

第二阶段 V1 已在自由设计工作区中提供：

- 减反、Bragg 高反和 F-P 共振三个引导式实验任务；
- 实验前预测、步骤进度和实验结论记录；
- 最多 8 条本机实验记录及最多 3 条历史曲线叠加比较；
- 极值、中心波长性能、高反带宽、透射峰 FWHM 与 Q 因子分析。

第二阶段 V2 已提供：

- 可选探针波长处的层内一维场强 `|E|²` 分布；
- 反射/透射相位光谱、各层光学厚度和单程/往返相位；
- 面向三个引导实验的透明阈值评价，并独立展示步骤、预测和结论完成情况。

物理计算只使用外层仓库的 `thinfilm/`。`Frontend/V3/PyThinFilm/` 是历史副本，不参与开发运行或打包。

## 本地运行

首次安装或依赖变化后，在 `Frontend/V3` 执行：

```powershell
py -m venv --clear .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
```

启动桌面端：

```powershell
cd Frontend\V3\frontend
npm run dev
```

自由设计接口为 `POST /api/designs/simulate`。请求使用 `schema_version: "1.0"`，膜层按 `layers` 数组顺序计算。

### 双 TMM 后端（Step 1）

统一设计接口支持可选字段：

```json
{
  "solver": "pythinfilm"
}
```

- `tmmcore`：平面膜光谱默认后端，负责 R/T/A；教学洞察仍由 PyThinFilm 生成，响应中的 `solver` 字段会明确记录两者分工；
- `pythinfilm`：兼容与对照后端，继续负责特殊模型及独立复验。

当前已将自由设计工作区的平面膜光谱默认切换到 `tmmcore`，但没有把后22例批量切换到 `tmmcore`。单层减反、Bragg、F-P，以及斜入射有损银膜的 s/p 结果均与 PyThinFilm 在 `1e-10` 绝对误差内一致。

开发环境使用系统 Node；打包环境由 Electron 以 Node 模式执行随包分发的桥接程序。`GET /api/diagnostics` 可检查 `tmmcore.available`、版本和实际桥接路径。

案例库接口：

- `GET /api/case-library`：默认返回 22 例公开目录、分类和接入模式；`include_archived=true` 可查询完整 40 例目录；
- `GET /api/case-library/{case_id}`：返回统一后的正式结果或证据详情；
- `POST /api/simulations`：供 18 个实时教学案例重新计算，现全部经过 tmmcore 光谱路径；其中 `moth_eye_effective_gradient` 与 `rugate_filter` 使用 PyThinFilm 生成离散切片，再交由 tmmcore 逐层计算，并在 `solver.discretization` 中标记近似方式。

教学案例现在同时返回四段式应用线路元数据：`learning_goal`（物理规律）、`coating_function`（膜系功能）、`application_scene`（工程场景）和 `design_task`（设计任务）。案例库会在参数区上方显示这条线路；它只改变教学信息架构，不改变原有计算结果。

40 个案例还返回 `system_experiment` 草案，绑定系统模板、复杂度、默认观察图和核心问题。该配置先作为教学信息架构使用，后续再由 Optiland 模板生成对应系统，不会把 40 个案例硬编码成 40 套前端逻辑。

案例库中的“带入自由设计”会把当前案例的膜层、材料角色、厚度、波段和入射条件转换为统一的 `DesignDraft`。实时案例在尚未计算时会先调用一次仿真；静态证据案例直接使用已保存的层结构。进入自由设计后，膜系仍可继续编辑，并由默认的 `tmmcore` 路径重新计算。

Optiland 系统分析接口：

- `GET /api/optiland/comparison`：首次访问时调用外部 Optiland 环境生成真实 MgF2/N-BK7 对照，之后读取缓存结果；前端工作区的“Optiland 系统分析”卡片会显示 2D/3D、Spot、PSF、MTF，平面膜的 R/T/A 仍由 PyThinFilm 膜系结果负责。
- `POST /api/optiland/system`：接收当前自由膜系草稿，按材料、启用层序和厚度重建 Optiland 系统；前端面板展开后才调用，并在草稿变化后防抖刷新。
- 案例带入自由设计时会携带 `system_template`；当前已实现 `single_lens_imaging` 基线和 `multi_element_imaging`（以及其手机/宽角变体）模板，其他模板安全回退到单透镜，避免在尚未验证时生成误导性系统图。
- 默认查找 `../optiland/.venv/Scripts/python.exe` 和 `../optiland`；如路径不同，可设置 `THINFILM_OPTILAND_ROOT` 与 `THINFILM_OPTILAND_PYTHON`。

## 验证

```powershell
cd Frontend\V3\backend
..\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm run typecheck
npm run build
npm run build:backend
```


## Windows 发布

在 `frontend/` 执行 `npm run dist`，依次完成依赖预检、后端冻结、GeneralTmm 独立运行时构建和 Electron 打包，输出安装版与便携版。随后执行 `npm run release:smoke` 验证 `release/win-unpacked` 中的实际计算路径。

依赖固定在根目录 `tools/release-dependencies.json`。外部 Optiland checkout 默认位于仓库同级 `optiland/`，构建时可通过 `THINFILM_OPTILAND_CHECKOUT` 指定；必须匹配清单的来源、提交和版本。GeneralTmm 使用校验 SHA256 的嵌入式 CPython，避免原生扩展在冻结环境中的访问冲突。后端端口默认 8122，可通过 `THINFILM_PORT` 配置独立后端进程。

详细验收范围见 [打包审计](../../docs/PACKAGING_AUDIT_20260923.md)。历史副本、虚拟环境、独立运行时和安装包不纳入源码提交。
