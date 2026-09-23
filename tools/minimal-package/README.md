# PythonFilm 精简项目包

此目录只包含当前 App 运行所需的源码、案例数据、材料表、Optiland 源码以及启动脚本。没有历史副本、测试、开发输出、旧安装包、虚拟环境或完整 `node_modules`。

## 环境

- Windows 10/11
- Python 3.11 及以上（当前开发环境验证为 Python 3.13）
- Node.js 20 及以上，npm
- 首次安装需网络下载依赖；安装后可以在本机使用

在此目录打开 PowerShell：

```powershell
.\安装依赖.ps1
.\启动PythonFilm.ps1
```

如 PowerShell 禁止执行脚本，可在当前终端使用 `powershell -ExecutionPolicy Bypass -File .\安装依赖.ps1` 和 `powershell -ExecutionPolicy Bypass -File .\启动PythonFilm.ps1`，无需修改系统策略。

安装脚本会创建 `Frontend/V3/.venv` 和 `Frontend/V3/frontend/node_modules`，这些目录并不包含在交付包里。启动时会同时启动本地 FastAPI 后端、Vite 和 Electron，默认端口 8122/5173；需要关闭时退出启动终端。

Optiland 是随包的源代码及本地 Python 环境运行，不依赖原工作区。此包是源码运行包，**不是免安装的便携 EXE**。RCWA、GeneralTmm、WPTherml 专用实验依赖也会安装。图像及计算结果写入本包 `Frontend/V3/backend/outputs`，该目录不含预存的开发输出。

App 默认公开 22 个教学案例；完整 40 例数据为开发归档内容，不等同于 40 例都已在教学界面开放。模型的教学适用范围保持在界面说明中。
