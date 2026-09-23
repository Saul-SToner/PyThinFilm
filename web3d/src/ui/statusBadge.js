export function renderStatusBadges(container, caseConfig) {
  container.innerHTML = "";

  const badges = [];

  // Geometry Status Badge
  if (caseConfig.geometry_status === "GEOMETRY_READY") {
    badges.push({ text: "GEOMETRY_VERIFIED", class: "badge-geometry-verified" });
  } else if (caseConfig.geometry_status === "GEOMETRY_MISMATCH") {
    badges.push({ text: "GEOMETRY_MISMATCH", class: "badge-blocked" });
  } else {
    badges.push({ text: "NOT_AUDITED", class: "badge-not-audited" });
  }

  // Physics Data Badge
  if (caseConfig.physics_data_status === "PHYSICS_DATA_READY") {
    badges.push({ text: "PHYSICS_DATA_AVAILABLE", class: "badge-physics-data-available" });
  } else if (caseConfig.physics_data_status === "EXTERNAL_DATA_REQUIRED") {
    badges.push({ text: "EXTERNAL_DATA_REQUIRED", class: "badge-external-data-required" });
  } else if (caseConfig.physics_data_status === "ILLUSTRATIVE_ONLY") {
    badges.push({ text: "ILLUSTRATIVE_ONLY", class: "badge-illustrative-only" });
  } else {
    badges.push({ text: "NOT_AUDITED", class: "badge-not-audited" });
  }

  // Python Reference Comparison Badge
  if (caseConfig.python_reference_comparison === "PASSED") {
    badges.push({ text: "PYTHON_REFERENCE_PASSED", class: "badge-python-reference-passed" });
  }

  // Render Badges
  badges.forEach((b) => {
    const span = document.createElement("span");
    span.className = `badge ${b.class}`;
    span.textContent = b.text;
    container.appendChild(span);
  });
}
