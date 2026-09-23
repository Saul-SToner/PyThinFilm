# Stage CV0：可视化数据契约

## 1. 目标与约束

本契约在现有正式 JSON 之上定义近似 REST API 的资源边界，使静态离线数据和未来本地 Python API 对前端表现一致。本阶段不修改 `web3d/public/results/*.json` 的数值、hash 或 schema，也不要求引入 FastAPI。

核心原则：

1. endpoint 是逻辑资源名，不等于当前必须存在 HTTP 服务；
2. 静态 provider 可从现有注册表和正式结果 JSON 投影资源；
3. 每个响应带 schema、caseId、provenance 和 availability；
4. 缺失数据显式返回 unavailable，不用零数组、教学示意或前端插值冒充；
5. 数据数组与共享 UI 状态分离，大数组不进入 URL 或 Store。

## 2. 逻辑端点

```text
/cases
/cases/{case_id}/capabilities
/cases/{case_id}/structure
/cases/{case_id}/spectrum
/cases/{case_id}/heatmap
/cases/{case_id}/field
/cases/{case_id}/export
```

建议静态目录近似为：

```text
web3d/public/api/v1/
  cases/index.json
  cases/{case_id}/capabilities.json
  cases/{case_id}/structure.json       # 有独立投影时
  cases/{case_id}/spectrum.json        # 有独立投影时
  cases/{case_id}/heatmap.json         # 仅有正式二维数据时
  cases/{case_id}/field.json           # 仅有正式场数据时
  cases/{case_id}/export.json
```

过渡期不要求复制大数组。`StaticCaseDataProvider` 可以把逻辑 `/structure`、`/spectrum` 和 `/export` 映射到同一个 `public/results/{case_id}.json`，由纯适配函数创建只读 view model。最小静态新增物只需 `index.json` 和每案例 `capabilities.json`；后续如生成拆分资源，必须由脚本从正式 JSON 确定性生成，不手工改数值。

## 3. 通用响应信封

成功且可用：

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.spectrum",
  "case_id": "app_wdm_filter",
  "availability": {
    "status": "available",
    "reason_code": null,
    "message": null
  },
  "provenance": {
    "calculation_source": "python_export",
    "source_schema_version": "1.0.0",
    "source_href": "./results/app_wdm_filter.json",
    "physics_input_hash": "...",
    "physics_result_hash": "...",
    "result_hash": "..."
  },
  "data": {}
}
```

不可用：

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.field",
  "case_id": "app_wdm_filter",
  "availability": {
    "status": "unavailable",
    "reason_code": "FIELD_DATA_NOT_EXPORTED",
    "message": "当前正式输出没有定量场数据。"
  },
  "provenance": null,
  "data": null
}
```

`status` 枚举：`available`、`unavailable`、`error`。`unavailable` 是正常能力状态；网络失败、解析失败或 schema 不合法才是 `error`。

建议 reason code：

- `RESOURCE_NOT_EXPORTED`
- `HEATMAP_DATA_NOT_EXPORTED`
- `FIELD_DATA_NOT_EXPORTED`
- `POLARIZATION_NOT_AVAILABLE`
- `ANGLE_NOT_AVAILABLE`
- `QUANTITY_NOT_AVAILABLE`
- `SCHEMA_UNSUPPORTED`
- `SOURCE_FILE_MISSING`

## 4. `/cases` 与 capabilities

`/cases` 返回导航所需的轻量元数据，不携带光谱数组：

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.index",
  "cases": [
    {
      "case_id": "app_wdm_filter",
      "display_name": "WDM 光通信密集波分复用滤光片",
      "category": "engineering_applications",
      "visualization_template": "defect-cavity",
      "template_mode": "DEFECT_CAVITY_MODE",
      "available_views": ["overview", "structure", "spectrum", "export"]
    }
  ]
}
```

`/capabilities` 是 Router 和控件的权威输入：

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.capabilities",
  "case_id": "app_wdm_filter",
  "default_view": "structure",
  "available_views": ["overview", "structure", "spectrum", "export"],
  "defaults": {
    "wavelength_nm": 1550.0,
    "angle_deg": 0.0,
    "polarization": "TE",
    "quantity": "T",
    "selected_layer": null
  },
  "views": {
    "overview": { "status": "available", "resource_href": "/cases/app_wdm_filter/capabilities" },
    "structure": {
      "status": "available",
      "resource_href": "/cases/app_wdm_filter/structure",
      "template": "defect-cavity",
      "template_mode": "DEFECT_CAVITY_MODE"
    },
    "spectrum": {
      "status": "available",
      "resource_href": "/cases/app_wdm_filter/spectrum",
      "quantities": ["R", "T", "A"],
      "polarizations": ["TE", "TM"],
      "angle_support": { "kind": "discrete", "values_deg": [0.0] }
    },
    "heatmap": { "status": "unavailable", "reason_code": "HEATMAP_DATA_NOT_EXPORTED" },
    "field": { "status": "unavailable", "reason_code": "FIELD_DATA_NOT_EXPORTED" },
    "export": { "status": "available", "resource_href": "/cases/app_wdm_filter/export" }
  }
}
```

`available_views` 可同时写入现有注册表作为导航摘要，但 `views` 对象才包含状态原因和数据维度。`migration_status` 继续保持原字段和原含义，不由本契约生成或修改。

## 5. `/structure`

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.structure",
  "case_id": "app_solar_cell_ar",
  "availability": { "status": "available", "reason_code": null, "message": null },
  "provenance": {},
  "data": {
    "ambient": { "name": "Air", "n": "1.0" },
    "substrate": { "name": "Si", "n": "Si" },
    "layers": [
      { "layer_id": "layer-0", "index": 0, "name": "SiO2", "type": null, "thickness_nm": 94.1781, "n": "1.46" }
    ],
    "coating_layer_count": 3,
    "visualization": {
      "template": "periodic-stack",
      "template_mode": "GENERIC_MULTILAYER_MODE",
      "animation_semantics": "TEACHING_ILLUSTRATION"
    }
  }
}
```

规则：

- `layer_id` 是前端稳定选择键，建议由层序号确定性生成；不改源层数据。
- `n` 保留可表达复数/材料标识的字符串，避免 JSON number 丢失源语义。
- `selectedLayer` 只能引用 `layer_id`；切案例后若不存在则置 `null`。
- `visualization.animation_semantics` 必须保留正式口径，不能因为进入 FieldWorkspace 而改变。

## 6. `/spectrum`

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.spectrum",
  "case_id": "app_laser_mirror",
  "availability": { "status": "available", "reason_code": null, "message": null },
  "provenance": {},
  "data": {
    "axes": {
      "wavelength_nm": [900.0, 901.0],
      "angle_deg": [0.0]
    },
    "series": {
      "TE": { "R": [0.9, 0.91], "T": [0.1, 0.09], "A": [0.0, 0.0] },
      "TM": { "R": [0.9, 0.91], "T": [0.1, 0.09], "A": [0.0, 0.0] }
    },
    "units": { "R": "fraction", "T": "fraction", "A": "fraction" },
    "metrics": {}
  }
}
```

示例数组仅说明形状，不替代正式数值。过渡适配器应零拷贝或只读引用源 `wavelength_nm`、`TE`、`TM` 和 `metrics`。

规则：

- 当前四案例只有一个正式角度切片，capability 应列为 `discrete: [0]`；注册表中的展示字符串如 `"0° / 30°"` 不等于当前结果 JSON 含两个角度。
- `quantity` 必须存在于所选 polarization 的 series 中。
- 光谱游标可线性插值用于显示当前读数和现有动态波的视觉振幅；插值结果标记为 `client_interpolated`，不能写回正式 JSON。
- 若未来 spectrum 按 query 获取，可使用 `?angle_deg=...`，响应仍需返回实际 resolved angle。

## 7. `/heatmap`

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.heatmap",
  "case_id": "example_case",
  "availability": { "status": "available", "reason_code": null, "message": null },
  "provenance": {},
  "data": {
    "x_axis": { "name": "wavelength_nm", "unit": "nm", "values": [] },
    "y_axis": { "name": "angle_deg", "unit": "deg", "values": [] },
    "quantity": "R",
    "polarization": "TE",
    "shape": [0, 0],
    "layout": "row-major-yx",
    "values": [],
    "value_unit": "fraction"
  }
}
```

规则：`shape[0] === y_axis.values.length`，`shape[1] === x_axis.values.length`，`values.length === shape[0] * shape[1]`。当前四个案例返回 `HEATMAP_DATA_NOT_EXPORTED`，不得通过重复一维光谱形成假热力图。

## 8. `/field`

一维场剖面建议形状：

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.field",
  "case_id": "example_case",
  "availability": { "status": "available", "reason_code": null, "message": null },
  "provenance": {},
  "data": {
    "dimensionality": "1d",
    "resolved_state": {
      "wavelength_nm": 1550.0,
      "angle_deg": 0.0,
      "polarization": "TE",
      "quantity": "normalized_abs_E2"
    },
    "axes": { "z_nm": [] },
    "values": [],
    "normalization": { "kind": "max", "reference": 1.0 },
    "layer_boundaries_nm": [],
    "field_semantics": "QUANTITATIVE_TMM_FIELD"
  }
}
```

规则：

- `field_semantics` 必须区别 `QUANTITATIVE_TMM_FIELD`、`EXTERNAL_SIMULATION_FIELD` 和 `TEACHING_ILLUSTRATION`。
- 只有前两类可使 FieldWorkspace 成为 available；教学波只能留在 StructureWorkspace。
- `resolved_state` 记录服务端/静态数据真正命中的状态，前端据此 reconcile Store。
- 当前四个工程案例没有该资源，应显式 unavailable。

## 9. `/export`

```json
{
  "schema_version": "cv0.1",
  "resource_type": "case.export",
  "case_id": "app_phone_lens_ar",
  "availability": { "status": "available", "reason_code": null, "message": null },
  "provenance": {},
  "data": {
    "artifacts": [
      {
        "artifact_id": "formal-result-json",
        "label": "正式结果 JSON",
        "media_type": "application/json",
        "href": "./results/app_phone_lens_ar.json",
        "source": "formal_python_export",
        "immutable": true
      }
    ],
    "client_exports": ["spectrum.csv", "spectrum.svg", "spectrum.png"]
  }
}
```

原始 JSON 下载保持原文件字节。CSV/SVG/PNG 是客户端派生制品，必须带 caseId、共享状态、源 result hash 和生成时间；不能覆盖正式 JSON。

## 10. SharedVisualizationState

规范模型：

```ts
type Polarization = "TE" | "TM";

interface SharedVisualizationState {
  caseId: string;
  wavelengthNm: number | null;
  angleDeg: number | null;
  polarization: Polarization;
  quantity: string;
  selectedLayer: string | null;
}
```

字段语义：

| 字段 | URL 键 | 语义与校验 |
|---|---|---|
| `caseId` | route segment | 必须存在于 case index |
| `wavelengthNm` | `wl` | 有限数；落在资源范围内；必要时钳制或回退默认值并记录 reconcile reason |
| `angleDeg` | `angle` | 有限数；当前只允许 capability 声明的离散值，不能从注册表字符串推断 |
| `polarization` | `pol` | `TE`/`TM` 且资源可用 |
| `quantity` | `q` | 工作区可解释的量，例如 `R`、`T`、`A`、`normalized_abs_E2` |
| `selectedLayer` | `layer` | structure 中的稳定 `layer_id`，无选择为 `null`/URL 中省略 |

`workspaceId` 属于 Router，不放入 SharedVisualizationState。播放状态、相机姿态、图表缩放、色标范围属于 workspace-local state，也不放入共享状态。

状态 reconcile 顺序：

1. 读取 route 候选值；
2. 获取 capabilities；
3. 以候选值、上一个案例状态、case defaults 的顺序选择首个合法值；
4. 再用具体资源的 resolved dimensions 校验；
5. 把规范值写回 Store 和 hash URL。

## 11. Provider 接口与离线/API 共存

```ts
interface CaseDataProvider {
  listCases(options?): Promise<CaseIndex>;
  getCapabilities(caseId, options?): Promise<CapabilitiesResource>;
  getStructure(caseId, options?): Promise<StructureResource>;
  getSpectrum(caseId, selection, options?): Promise<SpectrumResource>;
  getHeatmap(caseId, selection, options?): Promise<HeatmapResource>;
  getField(caseId, selection, options?): Promise<FieldResource>;
  getExport(caseId, selection, options?): Promise<ExportResource>;
}
```

实现：

- `StaticCaseDataProvider`：读取 `./api/v1/...`；过渡期用 `LegacyResultAdapter` 投影 `./data/case_registry.json` 与 `./results/{id}.json`。
- `PythonApiDataProvider`：使用相同逻辑路径访问配置的本地 base URL，例如 `http://127.0.0.1:{port}/api/v1`。
- `FallbackCaseDataProvider`：默认 API-first、static-fallback，但回退只发生在连接不可达/服务未启动；API 明确返回 4xx、schema error 或物理资源 unavailable 时不得静默改用静态数据掩盖问题。

每个资源响应都记录 `provider: "python-api" | "static" | "legacy-adapter"`。一次 workspace render 应使用同一资源的单一来源，禁止把 API 波长轴与静态 R/T 数组拼接。

建议启动配置：

```json
{
  "mode": "auto",
  "api_base_url": "http://127.0.0.1:8765/api/v1",
  "static_base_url": "./api/v1",
  "api_probe_timeout_ms": 500
}
```

`offline` 强制静态；`api` 强制本地 API 并显式报错；`auto` 探测 API 后选定 session provider。选定后不要对每个请求反复摇摆，避免同一会话数据来源不一致。

## 12. Schema 与一致性校验

前端运行时至少校验：

- `case_id` 与请求一致；
- `resource_type` 与 endpoint 一致；
- capabilities 的 `available_views` 与 `views.*.status` 一致；
- structure 层数与 layers 长度一致；
- spectrum 每条 series 长度与波长轴一致；
- heatmap shape/轴/values 一致；
- field axes/values/边界与 resolved state 完整；
- provenance hash 原样传递，不由前端重算后冒充源 hash。

构建期适配器还应验证四个现有案例的 `case_id`、`visualization_template`、`template_mode`、层数、波长点数和现有 hash 不变。
