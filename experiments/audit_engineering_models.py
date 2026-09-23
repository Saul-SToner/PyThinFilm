"""Audit all catalog system templates; runtime success is not engineering approval."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'Frontend/V3/backend'))
from app.case_catalog_service import SYSTEM_EXPERIMENTS, _optiland_system_family
from thinfilm.optiland_integration import OptilandBridge, CoatingStackInput, CoatingLayerInput, make_teaching_system_input

bridge = OptilandBridge(ROOT.parent / 'optiland')
rows = []
for template in sorted({v['system_template'] for v in SYSTEM_EXPERIMENTS.values()}):
    row = {'template': template, 'family': _optiland_system_family(template),
           'cases': [k for k,v in SYSTEM_EXPERIMENTS.items() if v['system_template'] == template]}
    try:
        outputs = []
        for coated in (False, True):
            stack = CoatingStackInput('Air', 'N-BK7', (CoatingLayerInput('MgF2', 100),) if coated else ())
            spec = make_teaching_system_input(template=template, name=template, glass_material_id='N-BK7', front_coating=stack, wavelength_um=.55)
            optic = bridge.build_system(spec)
            rays = optic.trace(Hx=0, Hy=0, wavelength=.55, num_rays=32, distribution='uniform')
            weights = np.asarray(bridge.api['be'].to_numpy(rays.i))
            outputs.append({'finite': bool(np.isfinite(weights).all()), 'mean_weight': float(np.nanmean(weights)),
                            'weight_in_0_1': bool(((weights >= -1e-8) & (weights <= 1+1e-8)).all())})
        geometry = [(s.radius_mm, s.thickness_mm, s.material_id, s.is_stop) for s in spec.surfaces]
        row.update(surface_count=len(spec.surfaces), coated_surfaces=sum(bool(s.coating and s.coating.layers) for s in spec.surfaces),
                   wavelength_count=len(spec.wavelengths_um), field_deg=spec.field_y_deg,
                   geometry_id=hashlib.sha256(json.dumps([geometry,spec.aperture_epd_mm,spec.field_y_deg]).encode()).hexdigest()[:12],
                   trace=outputs, runtime_pass=all(x['finite'] and x['weight_in_0_1'] for x in outputs))
    except Exception as exc:
        row.update(runtime_pass=False, error=str(exc))
    rows.append(row)
    print(template, row['runtime_pass'], flush=True)
out = ROOT / 'Frontend/V3/backend/outputs/engineering_model_audit.json'
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('templates',len(rows),'geometry variants',len({r.get('geometry_id') for r in rows}),'runtime passed',sum(r['runtime_pass'] for r in rows))
