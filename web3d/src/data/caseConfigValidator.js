export function validateCaseConfig(caseConfig) {
  if (!caseConfig || typeof caseConfig !== "object") {
    return { valid: false, reason: "案例配置对象无效或为空" };
  }

  const requiredFields = ["id", "display_name", "category", "visualization_template"];
  for (const field of requiredFields) {
    if (!caseConfig[field]) {
      return { valid: false, reason: `缺少必填字段: ${field}` };
    }
  }

  return { valid: true, reason: "" };
}
