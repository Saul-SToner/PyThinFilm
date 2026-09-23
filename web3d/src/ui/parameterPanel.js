export function renderParameterPanel(container, caseConfig) {
  if (!container || !caseConfig) return;

  container.innerHTML = `
    <div class="card">
      <h4>物理结构与参数</h4>
      <p><strong>名称：</strong>${caseConfig.display_name} (${caseConfig.id})</p>
      <p><strong>模板：</strong>${caseConfig.visualization_template}</p>
      <p><strong>结构：</strong>${caseConfig.structure || "未定义"}</p>
      <p><strong>波长：</strong>${caseConfig.incidence_angle || "550nm"}</p>
      <p><strong>偏振：</strong>${caseConfig.polarization_support || "TE/TM"}</p>
    </div>
  `;
}
