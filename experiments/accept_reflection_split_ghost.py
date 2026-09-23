"""Acceptance of existing app paths, not of unrelated Optiland examples."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from thinfilm.optiland_integration import OptilandBridge, CoatingStackInput, CoatingLayerInput, make_teaching_system_input
from experiments.optiland_ar_comparison import _trace_snapshot

bridge=OptilandBridge(ROOT.parent/'optiland')
stack=CoatingStackInput('Air','N-BK7',(CoatingLayerInput('MgF2',100),))
rows=[]
for template in ('folded_reflector','laser_expander','dbr_laser_cavity','dual_path_beamsplitter','single_lens_imaging','phone_camera_module','complex_camera_lens','wide_field_camera'):
    spec=make_teaching_system_input(template=template,name=template,glass_material_id='N-BK7',front_coating=stack,wavelength_um=.55)
    optic=bridge.build_system(spec)
    if any(s.radius_mm is not None for s in spec.surfaces):
        optic.updater.image_solve()
    snapshot=_trace_snapshot(optic,bridge.api,550,(0,1) if spec.field_y_deg else (0,0))
    directions=np.asarray(snapshot['N'])
    row={'template':template,'surface_count':len(spec.surfaces),'finite_exit_weights':bool(np.isfinite(snapshot['exit_intensity']).all()),
         'negative_z_directions':int(np.sum(directions<0)), 'image_z_mm':float(optic.surfaces[-1].geometry.cs.z),
         'lens_surface_radii_mm':[s.radius_mm for s in spec.surfaces[1:-1]],'field_deg':spec.field_y_deg}
    if template in ('folded_reflector','laser_expander','dbr_laser_cavity'):
        row.update(status='failed',reason='Existing builder uses only transmitted materials; no reflection interaction or folded/cavity path.')
    elif template=='dual_path_beamsplitter':
        row.update(status='failed',reason='Only one sequential optic and one image plane; no reflected branch or second detector.')
    else:
        row.update(status='failed',reason='App NSQ scene uses fixed r1=40/r2=-40, thickness=4, aperture=5, N-BK7 and detector z=41; it is not converted from the focused current optic.')
    rows.append(row)
out=ROOT/'Frontend/V3/backend/outputs/reflection_split_ghost_acceptance.json'
out.write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
