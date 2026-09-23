import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from thinfilm.optiland_integration import OptilandBridge,CoatingStackInput,CoatingLayerInput,make_teaching_system_input
bridge=OptilandBridge(ROOT.parent/'optiland')
from experiments.optiland_engineering_nsq import branch_scene,trace_branches,trace_matched_ghost
from experiments.optiland_ar_comparison import _trace_snapshot

rows=[]
for angle in (0.,45.):
    for mirror in (True,False):
        for r,t in ((.5,.5),(.8,.15)):
            scene,direction=branch_scene(r,t,550,angle,mirror)
            result=scene.trace(num_rays=2048,max_depth=4,seed=123)
            data=result.detectors['reflected']
            assert abs(data.total_flux-r)<1e-9,(data.total_flux,r)
            assert np.max(np.abs(np.column_stack([data.L,data.M,data.N])-direction))<1e-9
            if not mirror:
                assert abs(result.detectors['transmitted'].total_flux-t)<1e-9
            expected_loss=1-r if mirror else 1-r-t
            assert abs(result.total_flux_in-result.total_flux_detected-expected_loss)<1e-9
            rows.append(dict(test='branch',angle=angle,mirror=mirror,R=r,T=t,error=result.flux_conservation_error))
print('branch baselines passed',flush=True)
stack=CoatingStackInput('Air','N-BK7',(CoatingLayerInput('MgF2',100),))
for nm in (550,1064,1550):
    data=trace_branches(bridge,stack,nm,45,False)
    assert abs(data['reflected_flux']-data['expected_R'])<1e-9
    assert abs(data['transmitted_flux']-data['expected_T'])<1e-9
    rows.append({k:v for k,v in data.items() if k!='events'})
print('material branches passed',flush=True)
for template in ('single_lens_imaging','phone_camera_module','complex_camera_lens','wide_field_camera'):
    spec=make_teaching_system_input(template=template,name=template,glass_material_id='N-BK7',front_coating=stack,wavelength_um=.55)
    optic=bridge.build_system(spec); optic.updater.image_solve()
    data=trace_matched_ghost(bridge,spec,optic,550,count=20000,depth=24)
    rows.append({'template':template,**{k:v for k,v in data.items() if k!='ghost_map'}})
    assert len(data['geometry']['surfaces'])==len(spec.surfaces)-2
    assert data['ghost_flux']>=0
    assert data['full_flux']>0 and data['detected_ghost_paths']>0
    sequential=float(np.mean(_trace_snapshot(optic,bridge.api,550,(0,1) if spec.field_y_deg else (0,0))['exit_intensity']))
    assert abs(data['direct_flux']-sequential)<5*data['total_flux_standard_error']+.001
    assert data['ledger']['total_flux_lost']<.001
    deeper=trace_matched_ghost(bridge,spec,optic,550,count=20000,depth=32)
    assert abs(data['ghost_flux']-deeper['ghost_flux'])<.001
    finer=trace_matched_ghost(bridge,spec,optic,550,count=40000,depth=32,seed=2027,angle_step=.25)
    uncertainty=5*np.hypot(data['ghost_flux_standard_error'],finer['ghost_flux_standard_error'])
    assert abs(data['ghost_flux']-finer['ghost_flux'])<uncertainty+1e-5
    assert abs(data['full_flux']-finer['full_flux'])<5*np.hypot(data['total_flux_standard_error'],finer['total_flux_standard_error'])+.001
    rows.append({'template':template,'convergence':{'ghost_flux_delta':abs(data['ghost_flux']-finer['ghost_flux']),'five_sigma_bound':uncertainty,'depth_delta':abs(data['ghost_flux']-deeper['ghost_flux'])}})
    print(template,data['full_flux'],data['ghost_flux'],data['ledger'],flush=True)
out=ROOT/'Frontend/V3/backend/outputs/engineering_nsq_validation.json'
out.write_text(json.dumps(rows,indent=2),encoding='utf8')
