"""Render acceptance artifacts for the two baseline families."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.optiland_draft_render import run_render

out=ROOT/'Frontend/V3/backend/outputs/optiland_baselines'
out.mkdir(parents=True,exist_ok=True)
for template, nm, band in [('single_lens_imaging',550,(450,700)),('wide_field_camera',1064,(1000,1100)),('sensor_prefilter',1550,(1500,1600)),('spectral_camera',550,(540,560))]:
    if len(sys.argv)>1 and template!=sys.argv[1]:
        continue
    draft={'incident_material_id':'Air','substrate_material_id':'N-BK7','layers':[{'material_id':'MgF2','thickness_nm':100,'enabled':True}], 'system_template':template,'probe_wavelength_nm':nm,'spectrum':{'start_nm':band[0],'stop_nm':band[1],'points':351}}
    if template=='spectral_camera':
        from thinfilm.materials import material_complex_index
        def layer(material, fraction):
            n=float(material_complex_index(material, 550).real)
            return {'material_id':material,'thickness_nm':550*fraction/n,'enabled':True}
        left=[layer(m,.25) for m in ['TiO2','SiO2']*4]
        draft['layers']=left+[layer('SiO2',.5)]+list(reversed(left))
    folder=out/template
    folder.mkdir(exist_ok=True)
    source=folder/'draft.json'
    source.write_text(json.dumps(draft),encoding='utf8')
    result=json.loads(run_render(ROOT.parent/'optiland',folder,source).read_text(encoding='utf8'))
    assert result['analysis_conditions']['wavelength_nm']==nm
    assert result['sampling']['converged']
    assert result['energy_residue']<1e-8
    assert result['spectrum_color']['wavelength_range_nm']==list(band)
    for image in result['artifacts'].values():
        assert Path(image).read_bytes().startswith(b'\x89PNG')
    print(template,'passed',flush=True)
