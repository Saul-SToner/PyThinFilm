# PDRC 被动日间辐射冷却

这里放 PDRC 平面多层膜宽波段筛选和 COMSOL 结果摘要脚本。

常用根目录入口：

```bash
python run_pdrc_cooling_bundle.py
python run_pdrc_cooling_bundle.py --comsol-csv "path/to/pdrc_ir_window.csv"
```

当前建议先验证：

```text
太阳波段：0.3-2.5 um 低吸收
红外窗口：8-13 um 高发射
```
