# 竞赛演示路线

本文档为光学薄膜教学平台竞赛演示提供路线规划。

## 5 分钟演示路线

### 目标
快速展示平台核心功能，让评委了解平台能力。

### 路线

1. **开场** (30s)
   - 平台名称和定位
   - "完全自主的光学薄膜教学平台，不依赖 COMSOL"

2. **核心功能演示** (2min)
   - 运行 `run_teaching_demo.py --case single_ar`
   - 展示 R/T/A 光谱图
   - 展示膜层结构图

3. **工程应用案例** (1min)
   - 展示太阳能电池 AR 案例
   - 展示激光高反镜案例
   - 强调"从教学到工程"的完整覆盖

4. **交互性展示** (1min)
   - 展示 Plotly 交互图表
   - 展示参数调节效果

5. **技术亮点** (30s)
   - 270 个单元测试
   - TMM 向量化加速 1764x
   - RCWA 自主求解器

### 关键台词
- "这个平台完全用 Python 实现，不依赖任何商业软件"
- "所有核心算法都有单元测试保证正确性"
- "从教学演示到工程设计，一站式覆盖"

## 15 分钟答辩路线

### 目标
深入展示技术细节和创新点。

### 路线

1. **问题背景** (2min)
   - 光学薄膜在现代光学中的重要性
   - 教学中缺乏交互式工具的痛点

2. **平台架构** (2min)
   - 模块化设计：thinfilm / guided_grating
   - 三层架构：计算引擎 / 导出层 / 演示层

3. **核心算法** (3min)
   - TMM 传输矩阵法（向量化实现）
   - RCWA 有效介质理论
   - 性能优化：1764x 加速

4. **工程应用** (3min)
   - 5 个 TMM-only 案例详解
   - 每个案例的工程指标
   - 与实际应用的对应关系

5. **教育内容** (2min)
   - 参数说明系统
   - 设计原理文档
   - 公式库

6. **代码质量** (2min)
   - 270 个单元测试
   - CI/CD 集成
   - 代码审查和重构

7. **未来展望** (1min)
   - RCWA 完整实现
   - 更多工程案例
   - Web 交互界面

### 演示脚本

```python
# 1. 展示 TMM 核心
from thinfilm import simulate_report_design, plot_rta_spectrum
result = simulate_report_design("single_ar")
fig = plot_rta_spectrum(result["wavelength_nm"], result["R"], result["T"], result["A"])
fig.show()

# 2. 展示工程案例
from examples.applications import run_solar_cell_ar
solar = run_solar_cell_ar()
print(f"太阳能电池 AR: 平均反射率 {solar['metrics']['avg_R_300_1100nm']:.4f}")

# 3. 展示 RCWA
from guided_grating import rcwa_1d, GratingLayer
g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
r = rcwa_1d([1550.0], g)
print(f"光栅 R: {r['R'][0]:.4f}")

# 4. 展示教育内容
from thinfilm import get_design_help
print(get_design_help("single_ar"))
```

## TMM-only 工程案例路线

### 案例 1: 太阳能电池减反膜
```python
from examples.applications import run_solar_cell_ar
result = run_solar_cell_ar()
# 关键指标: 平均反射率、550nm反射率、R<2%带宽
```

### 案例 2: 通信 WDM 滤光片
```python
from examples.applications import run_wdm_filter
result = run_wdm_filter()
# 关键指标: FWHM、FSR、精细度、通道隔离
```

### 案例 3: 激光高反镜
```python
from examples.applications import run_laser_mirror
result = run_laser_mirror()
# 关键指标: 峰值反射率、停带宽度、周期对比
```

### 案例 4: 手机镜头 AR
```python
from examples.applications import run_phone_lens_ar
result = run_phone_lens_ar()
# 关键指标: 平均反射率、三色平衡、透射率
```

### 案例 5: 智能窗户
```python
from examples.applications import run_smart_window
result = run_smart_window()
# 关键指标: 可见光透过率、NIR反射率、SHGC
```

## RCWA 扩展路线

### 当前状态
- 1D 光栅 EMT 近似实现
- 支持 TE/TM 偏振
- 19 个单元测试

### 后续扩展
1. 完整 RCWA（支持衍射级次）
2. 2D 光栅支持
3. 与 COMSOL 验证对比

### 演示代码
```python
from guided_grating import rcwa_1d, GratingLayer, rcwa_convergence_test

# 基本计算
g = GratingLayer(980, 200, 1.45, 3.4, 0.55)
result = rcwa_1d(np.linspace(1400, 1700, 100), g, pol="TE")

# 收敛性测试
conv = rcwa_convergence_test(g, wavelength_nm=1550.0)
print(f"收敛: {conv['converged']}")
```

## 不依赖 COMSOL 的演示说明

### 平台定位
- **教学平台**: 完全自主 Python 实现
- **不依赖 COMSOL**: 所有核心计算由 Python 完成
- **COMSOL 仅作为**: 高级验证源、外部参考数据

### 演示时的话术
- "这个平台完全用 Python 实现，不需要安装任何商业软件"
- "所有算法都有单元测试保证正确性"
- "如果需要验证，可以导入 COMSOL 数据进行对比，但不是必需的"

### 技术优势
1. **自主可控**: 不依赖商业软件许可
2. **开源透明**: 所有代码可审查
3. **易于部署**: 仅需 Python 环境
4. **教学友好**: 学生可以查看和修改源码
