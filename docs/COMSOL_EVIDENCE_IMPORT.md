# COMSOL 外部证据导入规范

适用案例：

- `absorbing_surface_gain`
- `absorbing_surface_gain_trend`
- `advanced_ar_bundle`
- `porous_double_ar_topic_bundle`

这些案例展示正式外部计算证据，不使用替代模型曲线。现有发布结果已经包含来源角色、文件名、SHA-256 和可绘制数据；注册表中的 `EXTERNAL_DATA_REQUIRED` 仅表示原始计算依赖外部数据，不表示当前发布证据缺失。

## 获取模板

```text
GET /api/evidence/comsol-template/{case_id}
```

响应会列出允许的 `role`、必需物理量和推荐表头。

推荐光谱格式：

```csv
wavelength_nm,R,T,A
500,0.12,0.18,0.70
550,0.08,0.16,0.76
```

增透参考数据至少需要：

```csv
wavelength_nm,R
500,0.04
550,0.01
```

校验器同时识别 COMSOL 常见列名，例如 `lam/1[nm] (1)`、`abs(ewfd.S11)^2 (1)` 和 `theta (rad)`。

## 校验数据

```text
POST /api/evidence/validate-comsol-csv
Content-Type: application/json
```

```json
{
  "case_id": "advanced_ar_bundle",
  "role": "single_ar",
  "csv_text": "wavelength_nm,R\n500,0.04\n550,0.01\n"
}
```

校验要求：

- 至少两个有效数据点；
- 波长列必须存在；
- 增透案例必须包含反射率；
- 吸收表面案例至少包含 R、T、A 中的一项；
- 所有数值必须有限；
- R、T、A 必须位于 `[0, 1]`；
- 返回规范化列映射、数值范围和输入文本 SHA-256。

校验接口只验证并生成来源指纹，不自动覆盖仓库内正式证据。发布新证据时仍需保留原始文件、角色说明、生成脚本和结果哈希。
