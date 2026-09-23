export interface MaterialOption {
  material_id: string;
  display_name_zh: string;
  display_name_en: string;
  category: string;
  lambda_min_nm: number;
  lambda_max_nm: number;
  n_at_550nm: number;
  k_at_550nm: number;
}

export interface DesignLayer {
  id: string;
  material_id: string;
  thickness_nm: number;
  enabled: boolean;
}

export interface DesignDraft {
  schema_version: "1.0";
  solver?: "pythinfilm" | "tmmcore";
  incident_material_id: string;
  substrate_material_id: string;
  layers: DesignLayer[];
  spectrum: { start_nm: number; stop_nm: number; points: number };
  angle_deg: number;
  polarization: "s" | "p";
  out_of_range_policy: "error" | "clip";
  probe_wavelength_nm?: number;
  experiment_task_id?: string | null;
  /** Optional Optiland teaching-system template selected by a case. */
  system_template?: string;
  engineering_application?: { case_title: string; goal: string };
  /** Case-driven Optiland routing; disabled for pure thin-film experiments. */
  optiland?: {
    enabled: boolean;
    level: "deep" | "light" | "none";
    system_template?: string;
    system_family?: string;
    observables: string[];
  };
}

export interface DesignSimulationResult {
  schema_version: "1.0";
  request_id: string;
  design: DesignDraft & {
    layers: Array<DesignLayer & { n_center: number; k_center: number }>;
  };
  series: { wavelength_nm: number[]; R: number[]; T: number[]; A: number[] };
  summary: {
    layer_count: number;
    total_thickness_nm: number;
    max_energy_residue: number;
    mean_R: number;
    mean_T: number;
    mean_A: number;
  };
  metrics: {
    center_wavelength_nm: number;
    R: SpectrumExtrema;
    T: SpectrumExtrema;
    A: SpectrumExtrema;
    high_reflection_band: { threshold: number; start_nm: number; stop_nm: number; width_nm: number } | null;
    transmission_peak_linewidth: {
      status: "available" | "not_available";
      peak_wavelength_nm: number;
      peak_value: number;
      background: number;
      half_level: number;
      left_half_nm?: number | null;
      right_half_nm?: number | null;
      fwhm_nm: number | null;
      q_factor: number | null;
    };
  };
  field: {
    wavelength_nm: number;
    z_nm: number[];
    E2: number[];
    regions: string[];
    boundaries: Array<{ layer_id: string; material_id: string; start_nm: number; stop_nm: number }>;
    peak_E2: number;
    peak_z_nm: number;
    R: number;
    T: number;
    A: number;
    layer_phase: LayerPhase[];
  };
  phase: {
    wavelength_nm: number[];
    reflection_phase_deg: number[];
    reflection_phase_unwrapped_deg: number[];
    transmission_phase_deg: number[];
    probe: { wavelength_nm: number; reflection_phase_deg: number; transmission_phase_deg: number };
    layer_phase: LayerPhase[];
    explanations: string[];
  };
  evaluation: {
    status: "available" | "not_applicable";
    task_id: string | null;
    score: number | null;
    level: "excellent" | "qualified" | "developing" | null;
    criteria: Array<{ label: string; value: number | null; target: string; score: number; passed: boolean }>;
    feedback: string;
  };
  warnings: string[];
  solver: { spectral_engine: string; spectral_engine_version: string; teaching_insights_engine: string };
}

export interface LayerPhase {
  layer_id: string;
  material_id: string;
  optical_thickness_nm: number;
  one_way_phase_deg: number;
  round_trip_phase_deg: number;
}

export interface SpectrumExtrema {
  minimum: number;
  minimum_wavelength_nm: number;
  maximum: number;
  maximum_wavelength_nm: number;
  mean: number;
  at_center: number;
}

export interface ExperimentRecord {
  id: string;
  name: string;
  created_at: string;
  task_id: string;
  prediction: string;
  conclusion: string;
  draft: DesignDraft;
  result: DesignSimulationResult;
}
