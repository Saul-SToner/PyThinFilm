export async function loadCaseRegistry() {
  try {
    const res = await fetch("./data/case_registry.json");
    if (!res.ok) {
      throw new Error(`无法加载案例注册表: HTTP ${res.status}`);
    }
    const data = await res.json();
    return data;
  } catch (err) {
    console.error("loadCaseRegistry Error:", err);
    throw err;
  }
}
