export function renderEvidencePanel(container, caseConfig) {
  if (!container || !caseConfig) return;

  container.innerHTML = `
    <div class="card">
      <h4>物理证据与溯源信息</h4>
      <p><strong>源码位置：</strong>${caseConfig.source_file || "未知"}</p>
      <p><strong>源码符号：</strong>${caseConfig.source_symbol || "未知"}</p>
      <p><strong>物理机制：</strong>${caseConfig.physics_model || "未定义"}</p>
      <p><strong>计算来源：</strong>${caseConfig.calculation_source || "未校验"}</p>
      <p><strong>动画语义：</strong>${caseConfig.animation_semantics || "未校验"}</p>
      <p><strong>备注说明：</strong>${caseConfig.notes || "无"}</p>
    </div>
  `;
}
