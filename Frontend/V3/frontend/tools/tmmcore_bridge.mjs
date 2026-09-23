import { createInterface } from "node:readline";
import { jetConstant, tmm, tmmPhaseDispersion } from "tmmcore";

function calculate(request) {
  const wavelengths = request.wavelength_nm;
  const R = new Array(wavelengths.length);
  const T = new Array(wavelengths.length);
  const A = new Array(wavelengths.length);
  const reflectionPhaseDeg = new Array(wavelengths.length);
  const transmissionPhaseDeg = new Array(wavelengths.length);

  for (let index = 0; index < wavelengths.length; index += 1) {
    const layers = request.layers.map((layer) => ({
      n: layer.nk[index],
      d: layer.thickness_nm,
    }));
    const point = tmm(
      wavelengths[index],
      request.angle_deg,
      request.polarization,
      request.incident_nk[index],
      request.substrate_nk[index],
      layers,
    );
    R[index] = point.R;
    T[index] = point.T;
    A[index] = point.A;
    const phaseLayers = request.layers.map((layer) => ({
      indexJet: jetConstant(layer.nk[index][0], layer.nk[index][1]),
      thicknessNm: layer.thickness_nm,
    }));
    const phase = tmmPhaseDispersion(
      wavelengths[index],
      request.angle_deg,
      request.polarization,
      jetConstant(request.incident_nk[index][0], request.incident_nk[index][1]),
      jetConstant(request.substrate_nk[index][0], request.substrate_nk[index][1]),
      phaseLayers,
    );
    reflectionPhaseDeg[index] = phase.r?.phaseDeg ?? null;
    transmissionPhaseDeg[index] = phase.t?.phaseDeg ?? null;
  }

  return {
    R,
    T,
    A,
    reflection_phase_deg: reflectionPhaseDeg,
    transmission_phase_deg: transmissionPhaseDeg,
    engine: "tmmcore",
    version: "0.4.0",
  };
}

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  if (!line.trim()) continue;
  try {
    process.stdout.write(`${JSON.stringify({ ok: true, result: calculate(JSON.parse(line)) })}\n`);
  } catch (error) {
    const message = error instanceof Error ? error.stack ?? error.message : String(error);
    process.stdout.write(`${JSON.stringify({ ok: false, error: message })}\n`);
  }
}
