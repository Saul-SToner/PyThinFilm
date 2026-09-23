# Stage C.V1G：逐案例入口隔离

## 目标

40 个物理案例不再经由通用 `data-case-id` 入口选择运行时案例。每个 `web3d/apps/<slug>/` 目录拥有自己的模块入口，入口代码固定绑定唯一 `caseId`。

## 已移除的通用入口

- `web3d/src/apps/generic/main.js`
- `web3d/src/apps/evidence/main.js`
- `web3d/src/apps/shared/bootstrapEngineeringCase.js`

页面不再使用 `data-case-id` 决定加载哪个案例。

## 保留的基础设施

为保证 Renderer 单例、相机行为、材料颜色和资源释放一致，以下内容仍是底层基础设施，而不是案例选择器：

- `RendererLifecycle`
- `CameraManager`
- `SceneManager`
- 材料与视觉主题
- 正式 JSON 读取和公共资源释放工具

案例入口、固定 caseId、正式数据文件和场景声明均逐案例隔离。修改一个案例入口不会改变另一个案例绑定到哪个 caseId。

## 自动约束

`web3d/tests/standalone_entrypoints.test.js` 检查：

1. 40 个案例对应 40 个不同的模块绝对路径；
2. HTML 不包含 `data-case-id`；
3. 不引用旧的 generic/evidence 通用入口；
4. 入口不从 DOM 的 `dataset.caseId` 动态选择案例。

本阶段不修改 Python 物理计算、正式 JSON 数值、层序、膜层数量或 `migration_status`。
