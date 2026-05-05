# thinfilm 包说明

当前 `thinfilm/` 已收缩为三部分：

1. 教学主树正向仿真  
2. 通用 CSV / COMSOL 光谱读取  
3. 理论与 COMSOL / 实验对照验证

## 当前主要模块

```text
api.py         教学主树高层接口
education.py   平面多层膜正向仿真与导出
io.py          通用光谱 CSV 读取
validation.py  理论-参考曲线对照与误差分析
paths.py       输出路径工具
```

## 常用调用

教学案例仿真：

```python
from thinfilm import export_teaching_case_outputs

files = export_teaching_case_outputs("single_ar")
print(files)
```

理论与 COMSOL 对照：

```python
from pathlib import Path
from thinfilm import compare_teaching_case_to_reference, export_teaching_validation_result

result = compare_teaching_case_to_reference(
    "single_ar",
    Path(r"C:\path\to\AR_case.csv"),
    y_selector="R (1)",
    quantity="R",
    reference_label="COMSOL",
)
files = export_teaching_validation_result(result)
```

## 说明

- 反演主线代码与样本已从当前包结构中移出，不再作为仓库内主工作流保留。
- 若 PowerShell 中中文显示乱码，通常是终端编码问题，不代表文件损坏。
