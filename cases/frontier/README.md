# 前沿研究模型树

这里放前沿研究模型树导出脚本，用于组织 Tamm、PDRC 等不直接放进教学主树首页的模块。

常用根目录入口：

```bash
python run_frontier_model_tree.py
python run_frontier_model_tree.py --bundle
```

当前导出包含：

```text
roadmap.json
roadmap.txt
roadmap.png
```

其中 `roadmap.png` 用于汇报展示，当前口径为：

```text
PDRC：正结果模块，已完成真实材料宽波段验证，A_solar_weighted(ASTM G173)=0.0435，epsilon_8_13_avg=0.8044，cooling_score_weighted=0.7609。
Tamm/TPP：前沿探索模块。Tamm 界面态分支已完成判据建立与候选排除；TPP 反射型吸收器已获得正结果，d_spacer=320 nm、lambda=3.34 μm 时 A=1-R=0.9994。
```
