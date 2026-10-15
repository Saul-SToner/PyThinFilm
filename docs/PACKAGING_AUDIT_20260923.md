# Windows 打包审计（2026-09-23）

初次候选的 GeneralTmm 冻结运行时未通过验收，保留在 `release/PythonFilm-20260923-blocked`，不得分发。随后采用独立嵌入式 CPython 修复，并对新的安装版、便携版逐一验收。旧版 `release/PythonFilm-20260922-final` 未覆盖。

## 依赖与构建

- `tools/release-dependencies.json` 固定 Optiland 的 Git 来源、提交和安装版本，以及 tmmcore/RCWA/GeneralTmm/WPTherml 版本。
- `npm run build:backend` 首先运行 `tools/release_audit.py preflight`，版本、Optiland import 来源、RCWA/WPTherml 数据缺失时立即失败。
- PyInstaller 显式收集 `rcwa/nkData` 与 `wptherml/data`。旧版仅收录 Python 模块，RCWA 端点在解包后返回 HTTP 500，根因为缺失 `nkData/library.yml`。
- Optiland 来自仓库外的固定 checkout；GitHub 上的 PyThinFilm 分支本身不含该仓库。新构建机仍须先按清单克隆并安装 Optiland。

## 实际运行结果

从新建 `win-unpacked` 启动其内的冻结后端，使用随包的 Electron 作为 tmmcore Node 运行时，不调用开发环境 Python 或 Node：

| 功能 | 结果 |
| --- | --- |
| 后端健康检查与诊断 | 通过 |
| tmmcore 单层膜计算 | 通过 |
| RCWA 两点光栅计算 | 通过 |
| WPTherml 光谱计算 | 通过；求解器最少返回 10 点 |
| Optiland 单镜系统渲染 | 通过，返回图像资源 |
| GeneralTmm 薄膜计算 | **失败：进程以 0xC0000005 访问冲突退出** |

`tools/generaltmm_freeze_probe.py` 将问题缩小至上游 C++ 扩展与冻结运行时：独立 PyInstaller 程序可导入 GeneralTmm、构造 Tmm/膜层，但调用 `Sweep()` 或 `GetIntensityMatrix()` 都访问冲突；相同 API 在开发虚拟环境的测试中通过。因此不能把仅检查文件存在或 `importlib.find_spec` 的结果当成发布验收。

## 修复与复验

- 固定 SHA256 的 Python 3.13.1 Windows 嵌入式运行时随 App 分发；NumPy 2.5.3、eigency 3.4.0.7、GeneralTmm 1.3.1 和现有适配器置于其隔离目录。
- 冻结后端只通过 JSON 子进程委托 GeneralTmm 原生计算；没有改变求解器或 Tamm 物理模型。开发环境仍直接调用 GeneralTmm。
- 对两个最终 EXE 分别解压，逐项计算验收：tmmcore 单层膜、RCWA 光栅、WPTherml 光谱、Optiland 系统渲染、GeneralTmm 接口以及 Tamm 多层光谱与 601 点场分布，均通过。未借用开发机 Python 或 Node；测试端口随机分配，不干扰运行中的桌面端。
- 这是安装包内容的解压验收，并非另一台全新 Windows 机器上的交互安装和 GUI 验收。

## 后续发布门槛

1. 后续更换任何 Python、原生依赖、Optiland 提交或 npm 包时，重新执行依赖预检和完整计算验收。
2. 面向外部设备大规模分发前，再做一台全新 Windows 机器上的交互安装、便携版启动和 GUI 检查。
