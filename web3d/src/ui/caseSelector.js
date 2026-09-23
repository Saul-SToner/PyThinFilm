export function renderCaseSelector(container, cases, activeCaseId, onSelectCase) {
  container.innerHTML = "";

  cases.forEach((c) => {
    const item = document.createElement("div");
    item.className = `case-item ${c.id === activeCaseId ? "active" : ""}`;
    
    item.innerHTML = `
      <div class="case-item-title">${c.display_name}</div>
      <div class="case-item-meta">${c.id} | ${c.visualization_template}</div>
    `;

    item.addEventListener("click", () => {
      onSelectCase(c.id);
    });

    container.appendChild(item);
  });
}
