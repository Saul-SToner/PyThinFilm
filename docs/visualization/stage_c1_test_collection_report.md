# PyThinFilm 全案例 3D 动态可视化 — Stage C.1.1 测试收集与自动化测试套件审计报告

本报告记录对 Python pytest 测试收集数量与 Stage C.1.1 自动化测试的审计结果。

---

## 一、 测试收集与数量对比

1. **`py -m pytest --collect-only -q` 执行结果**：
   - 收集到 **`360`** 项测试（无任何测试被删除或漏载）。
   - 上一阶段 346 项测试，本阶段新增 14 项测试：
     * 6 项新增在 📄 [tests/test_web3d_stage_c1_exports.py](file:///C:/Users/L2791/Downloads/PyThinFilm/tests/test_web3d_stage_c1_exports.py)
     * 6 项新增在 📄 [tests/test_web3d_stage_c1_metrics.py](file:///C:/Users/L2791/Downloads/PyThinFilm/tests/test_web3d_stage_c1_metrics.py)
     * 2 项新增在 📄 [tests/test_web3d_equivalence_audit.py](file:///C:/Users/L2791/Downloads/PyThinFilm/tests/test_web3d_equivalence_audit.py)

2. **`py -m pytest tests/ -q` 执行日志**：
   - **`360 passed, 0 failed`** (2.15s)。

3. **`cd web3d; npm run test` Vitest 执行日志**：
   - **`8 test files passed (10 tests passed)`** (2.25s)（含 `stage_c1_binding.test.js` 与 10 案例 50 轮无缝切换 `ten_case_switching.test.js`）。

4. **`cd web3d; npm run build` Vite 构建**：
   - **`dist built in 675ms`**。
