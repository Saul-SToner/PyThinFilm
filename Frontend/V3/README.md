# PyThinFilm V3 桌面端

V3 同时保留两种工作区：

- **自由膜系设计**：编辑任意膜层、选择真实色散材料、查看 R/T/A 与 Three.js 三维结构。
- **40 例案例库**：18 个薄膜教学案例保留实时参数计算；另接入 1 个 EMT 虚拟实验、5 个工程应用和 16 个研究拓展案例的正式结果或证据数据。

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

### 自由设计 AI 问答

“分析结果”右上角的“问问本次结果”会将当前膜系、计算条件、指标与抽样光谱发送给后端，再由后端调用硅基流动 `deepseek-ai/DeepSeek-V4-Flash`。回复通过 SSE 流式展示，分别显示模型提供的思考内容与正式回答；回答支持 Markdown、表格和数学公式，可继续追问或停止生成。用户界面不提供 API Key 输入框。

开发者编辑 `Frontend/V3/backend/.env`，填入自己的 Key：

```dotenv
SILICONFLOW_API_KEY=你的APIKey
```

随后启动 `npm run dev`。后端直接读取该文件，修改 Key 后下一次提问即生效。`.env` 已被 Git 忽略；未填写时，问答接口会给出“请联系 APP 管理员”的提示。后端环境变量 `SILICONFLOW_API_KEY` 如已设置，会优先于 `.env`。密钥不会由问答接口返回。

### 小范围短期试用：临时内置 Key

如果接受安装包内的 Key **可以被提取和在 APP 外使用**，先在上述 `.env` 中填写专用于试用的 Key，再在 `Frontend/V3/frontend` 执行：

```powershell
npm run dist:temporary-ai-key
```

该命令仅在 Electron 打包阶段把 `.env` 复制到安装包的 `resources/backend/.env`，不会写入源码或 Git；普通 `npm run dist` 不复制 `.env`。不要复用你其它项目的 Key。发布前核对硅基流动账户的余额、用量和可用限制，发布后按计划在控制台作废 Key。**一周后作废会让所有旧安装包的问答同时失效**；Key 能否被滥用取决于作废前的剩余额度与限制，APP 内限流无法约束提取 Key 后的直接调用。

### 长期发布：服务端网关

长期发布时，当前安装包仍在用户电脑上启动本地计算后端，问答建议另行部署你管理的轻量网关 `app.ai_gateway:app`，仅在服务端的 `backend/.env` 中填写 `SILICONFLOW_API_KEY`。例如在服务器的 `Frontend/V3/backend` 目录运行：

```powershell
$env:THINFILM_AI_DAILY_REQUEST_LIMIT = "500"
..\.venv\Scripts\python.exe -m uvicorn app.ai_gateway:app --host 0.0.0.0 --port 8130
```

构建用户版前端前，将 `VITE_AI_API_BASE_URL` 设为这个网关的 HTTPS 地址，再运行 `npm run build`。网关设有每 IP 每分钟 12 次及每日总请求数上限；正式公网部署仍应在反向代理处配置访问控制，并在硅基流动侧设置费用上限。`DeepSeek-V4-Flash` 是计费模型，实际价格以硅基流动控制台为准。

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

- `GET /api/case-library`：返回 40 例目录、分类和接入模式；
- `GET /api/case-library/{case_id}`：返回统一后的正式结果或证据详情；
- `POST /api/simulations`：供 18 个实时教学案例重新计算，现全部经过 tmmcore 光谱路径；其中 `moth_eye_effective_gradient` 与 `rugate_filter` 使用 PyThinFilm 生成离散切片，再交由 tmmcore 逐层计算，并在 `solver.discretization` 中标记近似方式。

教学案例现在同时返回四段式应用线路元数据：`learning_goal`（物理规律）、`coating_function`（膜系功能）、`application_scene`（工程场景）和 `design_task`（设计任务）。案例库会在参数区上方显示这条线路；它只改变教学信息架构，不改变原有计算结果。

40 个案例还返回 `system_experiment` 草案，绑定系统模板、复杂度、默认观察图和核心问题。该配置先作为教学信息架构使用，后续再由 Optiland 模板生成对应系统，不会把 40 个案例硬编码成 40 套前端逻辑。

案例库中的“带入自由设计”会把当前案例的膜层、材料角色、厚度、波段和入射条件转换为统一的 `DesignDraft`。实时案例在尚未计算时会先调用一次仿真；静态证据案例直接使用已保存的层结构。进入自由设计后，膜系仍可继续编辑，并由默认的 `tmmcore` 路径重新计算。

Optiland 系统分析接口：

- `GET /api/optiland/comparison`：首次访问时调用外部 Optiland 环境生成真实 MgF2/N-BK7 对照，之后读取缓存结果；前端工作区的“Optiland 系统分析”卡片会显示 2D/3D、Spot、PSF、MTF，平面膜的 R/T/A 仍由 PyThinFilm 膜系结果负责。
- `POST /api/optiland/system`：接收当前自由膜系草稿，按材料、启用层序和厚度重建 Optiland 系统；前端面板展开后才调用，并在草稿变化后防抖刷新。
- 案例带入自由设计时会携带 `system_template`；当前已实现 `single_lens_imaging` 基线和 `multi_element_imaging`（以及其手机/宽角变体）模板，其他模板安全回退到单透镜，避免在尚未验证时生成误导性系统图。
- 源码开发版优先使用项目根目录 `optiland/` 和启动后端的 Python 环境（`Frontend/V3/.venv`）；若项目内无源码，则回退查找同级目录 `../optiland` 及其 `.venv`。也可通过 `THINFILM_OPTILAND_ROOT` 与 `THINFILM_OPTILAND_PYTHON` 显式指定。

## 验证

```powershell
cd Frontend\V3\backend
..\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm run typecheck
npm run build
npm run build:backend
```
