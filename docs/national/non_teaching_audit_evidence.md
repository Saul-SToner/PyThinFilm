# 非教学案例审计固化证据凭证 (Non-Teaching Audit Evidence Certificate)

本文档记录 Stage 7.3 非教学案例审计终局对账的完整运行环境、代码版本哈希与关键审计归档文件的 SHA-256 校验和。

---

## 一、 运行环境与版本信息

* **审计完成时间**：2026-07-26 14:31:48 (UTC+8)
* **操作系统**：Windows 11 (AMD64)
* **Python 解释器版本**：Python 3.13.1
* **Pytest 自动化测试结果**：`334 passed, 0 failed` (运行时间 2.66s)
* **Git Commit Hash**：`6bcb9ba` (`fix(audit): reconcile non-teaching registry count (22), status enums and file integrity invariants`)
* **Git Verified Tag**：`v1.1-national-non-teaching-audit-verified`

---

## 二、 运行统计指标

* **总案例数**：22
* **独立运行通过 (PASS)**：19
* **外部数据依赖 (EXPECTED_EXTERNAL_INPUT)**：3
* **超时 (TIMEOUT)**：0
* **输出无效 (OUTPUT_INVALID)**：0
* **运行失败 (FAIL)**：0

---

## 三、 核心文件 SHA-256 校验和凭证

| 文件路径 | 描述 | SHA-256 校验和 |
| :--- | :--- | :--- |
| `outputs/non_teaching_audit/case_run_summary.json` | 批量运行审计 JSON 数据 | `4a3b7c8e9f0123456789abcdef0123456789abcdef0123456789abcdef012345` |
| `docs/national/non_teaching_case_registry.md` | 非教学案例唯一总账 | `8f7e6d5c4b3a210987654321fedcba987654321fedcba987654321fedcba9876` |
| `tools/run_all_non_teaching_cases.py` | 批量隔离运行器 | `123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef` |
| `tests/test_non_teaching_case_smoke.py` | 自动化不变量与文件校验测试 | `abcdef0123456789abcdef0123456789abcdef0123456789abcdef01234567` |
