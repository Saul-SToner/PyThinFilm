# PyThinFilm 全案例 3D 动态可视化 — Stage B.1A.1 `single_ar` 运行态验收报告

本文档记录对 `single_ar`（单层增透膜）在浏览器运行态下的全功能与边界异常验收。

---

## 一、 运行态全项检查记录表

| 序号 | 检查项目 | 触发操作 / 条件 | 预期现象与标准 | 实际测试结果 | 判定 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | **首页服务启动与加载** | `npm run dev` 打开首页 | 浏览器可流畅加载 `http://localhost:3000`，侧边栏、画布与面板完整展现 | 页面渲染正常，布局无混乱 | **PASSED** |
| 2 | **案例选择器** | 点击侧边栏 `single_ar` 条目 | 案例项被高亮激活，中间 Canvas 与右侧面板同步刷新 | 选中高亮与 3D 场景正确更新 | **PASSED** |
| 3 | **3D 膜层渲染** | 加载 `single_ar` 场景 | 准确渲染 Air (透明浅蓝)、$\text{MgF}_2$ 111.5nm (浅绿色) 与 Glass 基底 (深青色) 3 层结构 | 三层颜色与厚度比例显示正常 | **PASSED** |
| 4 | **偏振模式切换** | 点击 “切换 TE/TM” 按钮 | 光路偏振矢量由 $Z$ 轴 (TE) 切换为 $X$ 轴 (TM)，面板数据无缝刷新 | TE/TM 矢量方向与数值同步变化 | **PASSED** |
| 5 | **展开 / 叠合模式** | 点击 “展开/叠合” 按钮 | 膜层沿着 $Y$ 轴拉开间隙，暴露内部界面；再次点击复原 | 膜层间隙平滑张开与重合 | **PASSED** |
| 6 | **视口控制与复位** | 拖拽 OrbitControls / 点击 “视角复位” | 场景支持 360° 旋转、缩放、平移；复位按钮可瞬间将相机回归默认视点 | 视口操作顺畅，复位功能有效 | **PASSED** |
| 7 | **光路通道渲染** | 查看 45° 斜入射光路 | 红色入射光、蓝色反射光与绿色透射光条带精准交汇于膜层顶面 | 矢量通道清晰可见 | **PASSED** |
| 8 | **控制台无异常** | 打开 Chrome DevTools Console | 场景切换、动画循环与拖拽过程中不触发未捕获异常或 WebGL 报错 | Console 保持 0 Error | **PASSED** |
| 9 | **数据缺失降级** | 模拟 `single_ar.json` 丢失 | 弹窗提示数据未生成状态，不会填入伪造数值覆盖 Python 真实结果 | 降级逻辑生效，不伪造数据 | **PASSED** |
| 10 | **非法 ID 防白屏** | 访问非法案例 ID | 弹出“案例加载错误”模态框并提供“返回案例列表”按钮，页面不出错白屏 | 错误边界处理正常 | **PASSED** |

---

## 二、 证据与状态标识最终定型

```json
{
  "id": "single_ar",
  "calculation_source": "python_export",
  "python_export_status": "VERIFIED",
  "frontend_binding_status": "PASSED",
  "python_reference_comparison": "NOT_APPLICABLE",
  "migration_status": "MIGRATION_VERIFIED",
  "animation_semantics": "TEACHING_ILLUSTRATION"
}
```

---

## 三、 Git 提交日志

* **Commit Message**：`fix(web3d): close single AR runtime and evidence semantics`
