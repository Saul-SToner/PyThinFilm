/**
 * Stage C.1.3 Narrowband Metric Binding Test (Vitest)
 *
 * Verifies that:
 * 1. narrowband_filter.json contains 17 layers (not 13).
 * 2. fp_single_halfwave.json contains 13 layers (control case).
 * 3. narrowband_filter TE FWHM < fp_single_halfwave TE FWHM (linewidth narrowing).
 * 4. narrowband_filter TE Q-factor > fp_single_halfwave TE Q-factor (quality increase).
 * 5. Both TE and TM linewidths are AVAILABLE in both JSON files.
 *
 * Evidence classification: VITEST_FRONTEND_UNIT_TEST
 * NOT runtime evidence — this tests JSON data binding only.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const PUBLIC = resolve(__dirname, '../public');

function loadJson(name) {
  const p = resolve(PUBLIC, 'results', `${name}.json`);
  return JSON.parse(readFileSync(p, 'utf-8'));
}

describe('Stage C.1.3 Narrowband Metric Binding', () => {
  it('narrowband_filter.json has 17 layers', () => {
    const data = loadJson('narrowband_filter');
    expect(data.layers).toHaveLength(17);
  });

  it('fp_single_halfwave.json has 13 layers', () => {
    const data = loadJson('fp_single_halfwave');
    expect(data.layers).toHaveLength(13);
  });

  it('narrowband_filter TE FWHM is available and narrower than fp_single_halfwave', () => {
    const fp = loadJson('fp_single_halfwave');
    const nb = loadJson('narrowband_filter');

    const fp_te = fp.case_specific_metrics.audited_linewidth_TE;
    const nb_te = nb.case_specific_metrics.audited_linewidth_TE;

    expect(fp_te.fwhm_status).toBe('AVAILABLE');
    expect(nb_te.fwhm_status).toBe('AVAILABLE');

    expect(nb_te.fwhm_nm).toBeLessThan(fp_te.fwhm_nm);
    expect(nb_te.q_factor).toBeGreaterThan(fp_te.q_factor);
  });

  it('narrowband_filter TM FWHM is available and narrower than fp_single_halfwave', () => {
    const fp = loadJson('fp_single_halfwave');
    const nb = loadJson('narrowband_filter');

    const fp_tm = fp.case_specific_metrics.audited_linewidth_TM;
    const nb_tm = nb.case_specific_metrics.audited_linewidth_TM;

    expect(fp_tm.fwhm_status).toBe('AVAILABLE');
    expect(nb_tm.fwhm_status).toBe('AVAILABLE');

    expect(nb_tm.fwhm_nm).toBeLessThan(fp_tm.fwhm_nm);
    expect(nb_tm.q_factor).toBeGreaterThan(fp_tm.q_factor);
  });

  it('narrowband_filter resonance_validation_status is PASSED', () => {
    const data = loadJson('narrowband_filter');
    expect(data.case_specific_metrics.resonance_validation_status).toBe('PASSED');
  });

  it('narrowband_filter audited_defect_peak_TE is present and within 485±2nm', () => {
    const data = loadJson('narrowband_filter');
    const peak = data.case_specific_metrics.audited_defect_peak_TE;
    expect(peak).toBeDefined();
    expect(peak.fwhm_status).toBe('AVAILABLE');
    const wl = peak.selected_peak_wavelength_nm;
    expect(wl).toBeGreaterThan(483);
    expect(wl).toBeLessThan(487);
  });
});
