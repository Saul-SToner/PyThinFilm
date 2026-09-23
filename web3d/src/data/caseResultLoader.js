export async function loadCaseResult(caseId) {
  try {
    const res = await fetch(`./results/${caseId}.json`);
    if (!res.ok) {
      return { available: false, data: null, reason: "结果 JSON 未生成或路径不存在" };
    }
    const data = await res.json();
    return { available: true, data, reason: "" };
  } catch (err) {
    return { available: false, data: null, reason: err.message };
  }
}
