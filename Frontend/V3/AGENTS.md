# 本地运行的双栏式薄膜光学物理仿真桌面 APP

## 技术栈

- Electron + React + TypeScript + Vite + Tailwind CSS + shadcn/ui

## 目录结构

V3/
├─ frontend/      # Electron 前端
├─ backend/       # FastAPI 后端
└─ PyThinFilm/    # 物理计算核心代码

## 目标

- 使用 Electron 构建 Windows 桌面端界面
- 使用 FastAPI 构建本地后端 HTTP API
- 使用 PyThinFilm 作为核心物理计算/薄膜仿真模块
- 实现左栏输入参数，右栏展示数值结果和图表

## 注意事项

- PyThinFilm 中的内容不允许修改，仅可被后端封装调用
- 不要把物理计算逻辑写进 Electron 前端
- 不要让前端直接操作 PyThinFilm
- 输出图片、CSV、报告等文件统一放在后端 outputs/ 目录
- 不确定 PyThinFilm 内部函数时，先阅读源码再封装，不要凭空假设函数名