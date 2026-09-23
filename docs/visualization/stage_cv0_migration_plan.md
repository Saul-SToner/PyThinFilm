# Stage CV0：可视化工作区迁移计划

## 1. 计划目标

把当前单页 Three.js 应用渐进迁移为：

```text
CaseOverview
StructureWorkspace
SpectrumWorkspace
HeatmapWorkspace
FieldWorkspace
ExportWorkspace
```

迁移采用“先建立边界，再搬运行态”的顺序。现有页面在 StructureWorkspace 验收通过前一直保留为可回退基线。本轮只产出计划，不执行下列文件操作。

## 2. 不变量

整个迁移期间必须保持：

- 不修改 `thinfilm/` 和 `examples/applications/` 的物理计算；
- 不修改 `web3d/public/results/*.json` 的正式数值、hash 和现有 schema；
- 不修改现有 Three.js 视觉、动态波算法、颜色、相机和模板语义；
- 不修改 `web3d/data/case_registry.json` 中任何现有 `migration_status`；
- 不把教学动画升级表述为定量场；
- 不开发智能窗；`app_smart_window` 继续保持当前未迁移状态；
- 没有正式二维数据时不开发或伪造热力图。

## 3. 分阶段实施

### Phase CV1：契约与兼容基线

目标：在不改变页面行为的前提下建立可测试的数据边界。

1. 新增数据 schema/validator、`CaseDataRepository`、`StaticCaseDataProvider` 和 `LegacyResultAdapter`。
2. 为四个工程案例生成 capabilities，初始 `available_views` 为 `overview/structure/spectrum/export`。
3. adapter 继续读取现有 registry 和正式 result JSON，不复制或修改数值。
4. 添加契约测试：资源形状、数组长度、caseId、模板、层数、hash 透传。
5. 保存当前四案例截图和 E2E 结果为视觉/运行态基线。

退出条件：原入口和所有现有测试通过；新 repository 返回的 structure/spectrum 与旧 JSON 逐项一致。

### Phase CV2：SharedVisualizationState

目标：把跨工作区物理选择从 `App` 字段抽离。

1. 新增 typed store、selector、action 和 reconcile 逻辑。
2. 接入 `caseId/wavelengthNm/angleDeg/polarization/quantity/selectedLayer`。
3. 用兼容 facade 保留 `App.currentPolarization`、`App.currentWavelengthNm` 和 `window.__WEB3D_DEBUG__.setWavelength()` 的外部行为。
4. 参数面板改为读 Store 与 capabilities；修复“波长显示角度”的绑定，但不改变物理数据。

退出条件：波长与偏振变化仍只更新现有动态波语义；切案例默认值 reconcile 可预测；无大数组或 Three.js 对象进入 Store。

### Phase CV3：VisualizationRouter 与 Shell

目标：建立六工作区导航骨架，不迁移 Three.js 视觉。

1. 新增 hash router 和 `VisualizationShell`。
2. 支持 `#/cases/{caseId}/{workspace}` 与 hash 内状态参数。
3. 首次读取旧 `?case=` 并重定向到对应 `structure` hash。
4. Router 根据 capabilities 隐藏/禁用不可用视图；不可用深链显示原因并回退。
5. 加入前进/后退、刷新、未知路由和 URL round-trip 测试。

退出条件：旧 E2E 的 `/?case=app_*` 仍进入正确案例；复制 hash URL 可恢复案例、工作区和共享状态。

### Phase CV4：迁移 StructureWorkspace

目标：把现有运行页面原样装入工作区生命周期。

1. 将 Three.js 初始化、模板注册、控制按钮、动画 loop 和销毁逻辑从单体 App 搬入 `StructureWorkspace`/`StructureRuntime`。
2. 保留 `core/`、`templates/` 和当前视觉 CSS；只移动编排，不改渲染参数。
3. 波长和偏振通过 Store selector 传入现有模板方法。
4. 切离结构工作区时暂停 loop 并清理监听；切回时保证 renderer 数量和 context 行为符合基线。
5. 保留 debug facade 直到新 E2E 完全覆盖。

退出条件：四个工程案例截图无非预期视觉差异；动态波、TE/TM、播放/暂停、展开、视角复位、50 次案例切换测试通过。

### Phase CV5：Overview、Spectrum 与 Export

目标：先实现已有正式数据完整支持的工作区。

1. `CaseOverview` 展示案例元数据、capabilities、metrics 和 provenance。
2. `SpectrumWorkspace` 用 SVG 显示现有 R/T/A；游标更新 `wavelengthNm`，不触发新物理计算。
3. `ExportWorkspace` 提供原始正式 JSON 下载及带 provenance 的客户端 CSV/SVG/PNG 派生导出。
4. 工作区间验证波长、角度、偏振和 quantity 传递。

退出条件：四案例 `overview/structure/spectrum/export` 可导航；WDM 在 Spectrum 选 1550 nm 后进入 Structure，动态透射波仍绑定同一状态。

### Phase CV6：Heatmap/Field 插槽，保持关闭

目标：只建立 unavailable 状态和空工作区边界，不开发可视化。

1. Router 能识别 `heatmap`/`field` 工作区 id。
2. 当前四案例 capabilities 明确 unavailable 及 reason code。
3. 未经 schema 验证的资源不允许打开工作区。
4. 等未来正式数据出现后再单独立项实现渲染器和验收。

退出条件：不可用深链行为清晰，不产生空 Canvas、不使用示意数据占位。

### Phase CV7：可选本地 Python API

目标：增加数据来源，不改变离线能力。

1. Python 侧若引入 API，仅实现数据读取/已有计算入口的薄适配层，URL 与静态逻辑端点一致。
2. 新增 `PythonApiDataProvider` 和 session 级 `auto/api/offline` 选择。
3. API 不可达时 `auto` 回退静态；API schema 错误不静默回退。
4. 打包产物始终携带静态 registry、capabilities 和四案例正式 JSON。

退出条件：断网且 Python 服务未启动时四案例仍完整离线运行；连接 API 时相同 route/store/workspace 无需改代码。

## 4. 建议文件布局

以下是实施后的目标结构，不代表本轮已创建或移动代码文件：

```text
web3d/src/
  app/
    bootstrap.js                       # 新建：最小启动入口
    VisualizationShell.js             # 新建：全局布局与 outlet
    VisualizationRouter.js            # 新建：hash 路由
    workspaceRegistry.js               # 新建：工作区懒加载映射
  state/
    SharedVisualizationState.js        # 新建：store/actions/selectors
    reconcileCaseState.js              # 新建：按 capability 归一化
    routeStateCodec.js                 # 新建：URL 编解码
  data/
    CaseDataRepository.js              # 新建
    StaticCaseDataProvider.js           # 新建
    PythonApiDataProvider.js            # 新建（CV7）
    FallbackCaseDataProvider.js         # 新建（CV7）
    LegacyResultAdapter.js              # 新建
    contracts/                          # 新建：resource validators
    registryLoader.js                   # 保留，后续由 static provider 封装
    caseResultLoader.js                 # 保留兼容，稳定后内部转发 repository
    caseConfigValidator.js              # 保留并扩展新 schema validator，不改旧规则
  workspaces/
    CaseOverview/
    StructureWorkspace/
      StructureWorkspace.js            # 新建
      StructureRuntime.js              # 新建：从 main.js 搬 Three.js 编排
      StructureTemplateRegistry.js      # 新建：从 main.js 搬 templateMap
    SpectrumWorkspace/
    HeatmapWorkspace/                   # 先只有 unavailable 边界
    FieldWorkspace/                     # 先只有 unavailable 边界
    ExportWorkspace/
  components/
    CaseSelector.js                     # 可从 ui/caseSelector.js 渐进迁移
    SharedParameterPanel.js             # 替代旧 parameterPanel
    EvidencePanel.js                    # 从当前资源 provenance 渲染
    WorkspaceTabs.js
  core/                                 # 保留原路径和实现
  templates/                            # 保留原路径和视觉实现
  ui/                                   # 过渡期保留；逐个转发/弃用，不一次性移动
  main.js                               # 保留为 bootstrap 兼容入口，最终缩为数行

web3d/public/
  results/                              # 原样保留：正式 JSON 权威源
  data/case_registry.json               # 原样保留同步产物
  api/v1/cases/                         # 新建：轻量 index/capabilities/可选投影

web3d/data/
  case_registry.json                    # 保留权威注册表；未来仅新增 available_views

web3d/tests/
  contracts/                            # 新建
  router/                               # 新建
  state/                                # 新建
  workspaces/                           # 新建
  legacy/                               # 可移动旧测试，或保持原位避免无价值 diff
```

### 文件处理清单

| 动作 | 文件/目录 | 原因 |
|---|---|---|
| 新建 | `app/`、`state/`、repository/provider/contracts、`workspaces/` | 建立导航、共享状态、数据和渲染生命周期边界 |
| 逻辑移动 | `main.js` 的模板映射、引擎初始化、loop、dispose 到 StructureWorkspace | 解除单体 App 耦合；不改视觉代码 |
| 渐进移动 | `ui/caseSelector.js`、`parameterPanel.js`、`evidencePanel.js` 到 components | 让面板依赖 Store/resource，而非 App/caseConfig |
| 保留 | `core/`、`templates/`、`app.css` 中现有 Three.js 视觉规则 | 守住已验收运行态与视觉基线 |
| 保留 | `public/results/`、`data/case_registry.json`、同步脚本 | 保持正式数据和现有注册链路 |
| 保留兼容 | `main.js`、旧 loaders、`window.__WEB3D_DEBUG__` | 允许分阶段迁移和旧测试继续运行 |
| 不创建 | 当前四案例的 heatmap/field 数值文件 | 无正式数据，不伪造能力 |

不建议一开始物理移动旧文件。先让旧模块通过 facade 调用新边界，测试稳定后再移动，可降低 import 路径和视觉快照的大面积变化。

## 5. available_views 迁移方式

第一步由生成/校验脚本为四个案例提出以下增量字段：

```json
"available_views": ["overview", "structure", "spectrum", "export"]
```

约束：

- 这是新增导航能力字段，不触碰 `migration_status`；
- 源注册表与 `public/data` 同步副本继续由现有脚本保持一致；
- capabilities 生成器验证 `available_views` 与实际静态资源/legacy adapter 能力一致；
- 不为 `app_smart_window` 做迁移或能力补齐；
- 其余案例应另行审计，不因模板名存在就批量开放 spectrum/field。

## 6. 测试与验收矩阵

| 层级 | 必测项 |
|---|---|
| Contract | 四案例 caseId、schema、层数、波长点数、TE/TM 数组长度、hash/provenance 透传 |
| State | 六字段校验、切案例 reconcile、非法 URL、selectedLayer 失效、离散角度限制 |
| Router | hash parse/serialize、旧 `?case=`、刷新、前进/后退、不可用工作区回退 |
| Repository | offline、API 可用、API 不可达回退、API schema error 不回退、AbortController |
| Structure | 原模板/template_mode、单 renderer、dispose、动态波、偏振、WDM 波长振幅 |
| Spectrum | R/T/A 选择、光标同步 wavelength、无数据外推、SVG 导出元数据 |
| Cross-workspace | Spectrum→Structure、Heatmap→Spectrum（未来）、Structure→Export 状态一致 |
| E2E | 四案例旧 query 入口和新 hash 入口、连续切换、无 console/page error |
| Visual QA | 四案例结构工作区截图与当前基线比较；允许布局外壳变化，不允许 Three.js 内容变化 |

四案例锁定值至少包括现有测试已覆盖的层数、模板模式和关键 metrics；不要在新测试中重新四舍五入后替换正式 JSON。

## 7. 风险与回滚

| 风险 | 防护 | 回滚点 |
|---|---|---|
| 路由后旧桌面深链失效 | `?case=` 启动桥 + hash E2E | 保留旧 main 启动分支 |
| 切工作区造成多个 WebGL context | StructureWorkspace 独占 renderer，生命周期计数测试 | 暂时保持结构工作区常驻但暂停 loop |
| API/静态数据混用 | session provider + resource provenance | 强制 `offline` 模式 |
| 共享状态选择了不存在的切片 | capability reconcile + resolved_state | 回退案例默认并提示 |
| Field 过度声明 | field schema/status 门禁 | capabilities 保持 unavailable |
| 注册表复制不一致 | 延续 `sync-registry.mjs`，构建前校验 | 继续以 `web3d/data` 为权威源 |

每个 Phase 应形成独立可回滚提交。任何阶段若结构视觉或正式 JSON diff 出现，停止迁移并回到上一个通过基线的阶段。

## 8. 推荐实施顺序摘要

```text
契约/适配器
  → 共享状态
  → hash Router + Shell
  → 原样迁移 StructureWorkspace
  → Overview/Spectrum/Export
  → Heatmap/Field 保持 capability-gated
  → 可选 Python API provider
```

这一顺序先保护现有四案例和离线数据，再增加工作区；不会要求本轮之外提前修改物理计算、正式 JSON 或 Three.js 视觉。

## 9. 本轮停止点

Stage CV0 的交付物仅为本审计、数据契约和迁移计划。完成文档校验后停止，不进入 CV1 实施。
