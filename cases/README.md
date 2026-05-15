# cases 目录

`cases/` 按专题收纳具体运行脚本。仓库根目录仍保留同名 `run_*.py` 作为稳定入口，方便旧命令、README 和 CI 继续使用。

推荐理解方式：

```text
根目录 run_*.py      稳定入口，只做转发
cases/*/run_*.py    具体专题运行代码
thinfilm/           薄膜教学、验证和研究分析库
guided_grating/     光栅波导支线库
```

每个具体脚本顶部都带有轻量路径引导，用于在直接运行 `cases/*/run_*.py` 时自动把仓库根目录加入 Python 导入路径。因此下面两种写法都可用：

```bash
python run_teaching_demo.py --list
python cases/teaching/run_teaching_demo.py --list
```

## 分组

- `teaching/`：教学主树、教学验证和性能总包。
- `guided_grating/`：光栅波导支线。
- `advanced_ar/`：高级减反、多孔双层、rugate 表格。
- `absorbing_surface/`：粗糙/准随机吸收表面。
- `tamm/`：Tamm 相位、候选对和界面窗口分析。
- `pdrc/`：PDRC 被动日间辐射冷却模块。
- `frontier/`：前沿研究模型树。
