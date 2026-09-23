"""Native Optiland baselines: wavelength/field, Fresnel, focus, FP sampling."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from thinfilm.optiland_integration import OptilandBridge, CoatingStackInput, CoatingLayerInput, make_teaching_system_input
from experiments.optiland_ar_comparison import _trace_snapshot, _spot_data
from experiments.optiland_draft_render import _stack_spectrum
from experiments.optiland_sampling import sample_spectrum

bridge = OptilandBridge(ROOT.parent / 'optiland')
rows = []
for nm in (550., 1064., 1550.):
    for template in ('single_lens_imaging', 'wide_field_camera', 'sensor_prefilter'):
        fields = [(0.,0.),(0.,1.)] if template == 'wide_field_camera' else [(0.,0.)]
        optics=[]
        stacks=[]
        for coated in (False,True):
            stack=CoatingStackInput('Air','N-BK7',(CoatingLayerInput('MgF2',100),) if coated else ())
            spec=make_teaching_system_input(template=template,name=template,glass_material_id='N-BK7',front_coating=stack,wavelength_um=nm/1000)
            optic=bridge.build_system(spec)
            if template!='sensor_prefilter':
                optic.updater.image_solve()
                y,_=optic.paraxial.marginal_ray()
                assert abs(float(y[-1,0]))<1e-8
            optics.append(optic)
            stacks.append(stack)
        assert abs(float(optics[0].surfaces[-1].geometry.cs.z)-float(optics[1].surfaces[-1].geometry.cs.z))<1e-10
        for field in fields:
            traces=[_trace_snapshot(o,bridge.api,nm,field) for o in optics]
            spots=[_spot_data(o,bridge.api,nm,field) for o in optics]
            for trace in traces:
                assert np.isfinite(trace['exit_intensity']).all()
                assert np.all((trace['exit_intensity']>=0)&(trace['exit_intensity']<=1+1e-8))
            assert np.allclose(spots[0]['x_mm'],spots[1]['x_mm'],atol=1e-9)
            assert np.allclose(spots[0]['y_mm'],spots[1]['y_mm'],atol=1e-9)
            mean=[float(np.mean(t['exit_intensity'])) for t in traces]
            if template=='sensor_prefilter':
                rear=bridge.build_coating(CoatingStackInput('N-BK7','Air'))
                rear_t=_stack_spectrum(rear.stack,np.array([nm]))[1][0]
                for stack, actual in zip(stacks,mean):
                    front_t=_stack_spectrum(bridge.build_coating(stack).stack,np.array([nm]))[1][0]
                    assert abs(actual-front_t*rear_t)<1e-8
            rows.append(dict(template=template,wavelength_nm=nm,field=field,throughput=mean,status='passed'))

# Constant-index, lossless symmetric FP cavity compared to analytic Airy law.
# A deliberately off-grid narrow resonance tests peak recovery.
from optiland.materials import IdealMaterial
from optiland.coatings import ThinFilmCoating
n=3.5
d=555.123/(2*n)*80
coating=ThinFilmCoating(IdealMaterial(n=1),IdealMaterial(n=1),layers=[(IdealMaterial(n=n),d,'cavity')])
grid, values, evidence=sample_spectrum(lambda wl:_stack_spectrum(coating.stack,wl),550,560,351)
r=((n-1)/(n+1))**2
analytic=1/(1+4*r/(1-r)**2*np.sin(2*np.pi*n*d/grid)**2)
assert np.max(np.abs(values[1]-analytic))<1e-9
assert np.max(np.abs(values.sum(axis=0)-1))<1e-9
assert evidence['converged']
assert abs(float(grid[np.argmax(values[1])])-555.123)<2*evidence['max_step_nm']
rows.append(dict(template='analytic_fp',status='passed',sampling=evidence))
out=ROOT/'Frontend/V3/backend/outputs/optiland_baseline_validation.json'
out.write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
