# 仓库协作说明

完整项目说明请以：

[README.md](README.md)

为准。

## 1. 当前主线

当前仓库保留两条主线：

1. 教学仿真主树
2. 光栅波导研究支线

## 2. 平台边界

当前统一约定：

```text
教学平台只展示教学主树
不暴露厚度反演入口
仓库内不再保留反演样本 CSV
```

## 3. 目录重点

```text
thinfilm/
guided_grating/
run_teaching_demo.py
run_guided_grating_demo.py
data/
```

## 4. 前端对接

前端或 APP 同学优先对接：

```text
thinfilm/api.py
~/thinfilm_outputs/teaching_main_branch_catalog.json
```

## 5. 理论验证

当前验证入口在：

```text
thinfilm/validation.py
```

推荐优先做三类对照：

1. 单层减反膜
2. F-P 滤光片
3. 高反膜

## 6. 光栅波导支线

当前支线已支持：

1. COMSOL 单谱读取
2. COMSOL 联合扫描读取
3. 自动筛选最接近目标波长的参数点

例如：

```bash
python run_guided_grating_demo.py --sweep-csv "path/to/2d.csv" --target-wavelength 1550
```

如果第二列不是 `period`，可显式指定参数名：

```bash
python run_guided_grating_demo.py --sweep-csv "path/to/8new.csv" --sweep-name fill_factor --target-wavelength 1550
```

## 7. 反演样本备份

旧反演样本已移出仓库；如需复查，请使用仓库外的个人备份。

## 8. 测试

运行全部测试：

```bash
python -m pytest tests/ -v
```

运行单个测试文件：

```bash
python -m pytest tests/test_tmm_core.py -v
```

快速验证（仅 TMM 核心）：

```bash
python -m pytest tests/test_tmm_core.py -q
```

测试文件结构：

```text
tests/
  test_tmm_core.py           TMM 传输矩阵核心（34 用例）
  test_tmm_vectorized.py     向量化 vs 标量数值一致性（14 用例）
  test_real_materials.py     真实材料加载与色散 TMM（17 用例）
  test_materials_cache.py    材料缓存机制（12 用例）
  test_io.py                 CSV I/O 解析（16 用例）
  test_simulate_report_design.py  全 design_type 分支覆盖（40 用例）
  test_guided_grating.py     光栅波导模块（55 用例）
  test_tamm_phase.py         Tamm 反射相位计算（14 用例）
  test_pdrc.py               PDRC surrogate + 真实材料仿真（18 用例）
```

性能基线：

```bash
python benchmarks/performance_baseline.py
```

## 9. 说明

如果 `PowerShell` 里中文显示乱码，通常是终端编码问题，不代表文件损坏。仓库内的 `README.md` 和 `AGENTS.md` 应视为 UTF-8 正常内容。
