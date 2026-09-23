"""Native NSQ reflection, zero-thickness splitter and matched coaxial lenses.

NumPy, monochromatic, unpolarized power transport. Coated curved surfaces use
explicit angular bins and reverse layer ordering for reverse incidence.
"""
import json
from pathlib import Path
import numpy as np
from optiland import nonsequential as nsq
from optiland.coordinate_system import CoordinateSystem as CS
from optiland.coatings import SimpleCoating
from optiland.nonsequential.ir.scene_ir import SamplingPolicy
from thinfilm.optiland_integration import CoatingStackInput


def ledger(result):
    return {k: float(getattr(result,k)) for k in (
        'total_flux_in','total_flux_detected','total_flux_absorbed',
        'total_flux_bulk_absorbed','total_flux_escaped','total_flux_lost','flux_conservation_error')}


def rt(bridge, stack, nm, angle):
    coating=bridge.build_coating(stack)
    vals=[coating.stack.compute_rtRAT_nm_deg(np.array([nm]),np.atleast_1d(angle),p) for p in ('s','p')]
    return tuple(np.mean([np.asarray(v[k]).reshape(-1) for v in vals],axis=0) for k in ('R','T'))


def branch_scene(reflectance, transmittance, nm, angle=45., mirror=False):
    """Plane in air, source along +z, R detector on vector reflection direction.

    Splitter is a zero-thickness effective film, no glass plate displacement.
    Mirror is opaque: non-reflected flux is loss, not separately inferred A.
    """
    scene=nsq.NSQScene()
    scene.sampling_policy=SamplingPolicy(split_depth=1,rr_start_flux=0)
    scene.add_source('source',CS(z=-10),nsq.CollimatedSourceConfig(nsq.Spectrum.monochromatic(nm/1000),aperture_radius=.5))
    tilt=np.deg2rad(angle)
    cs=CS(ry=tilt)
    if mirror:
        scene.add_mirror('mirror',cs,nsq.MirrorConfig(radius=np.inf,reflectance=reflectance,aperture_radius=5))
    else:
        scene.add_component('splitter',nsq.RefractiveComponent(cs,nsq.ConicGeometry(np.inf,0,5),nsq.NSQMaterial(),nsq.NSQMaterial(),coating=SimpleCoating(reflectance=reflectance,transmittance=transmittance)))
    # CoordinateSystem rotates local +z into (sin(ry),0,cos(ry)).
    normal=np.array([np.sin(tilt),0,np.cos(tilt)])
    reflected=np.array([0.,0.,1.])-2*normal[2]*normal
    scene.add_detector('reflected',CS(x=20*reflected[0],z=20*reflected[2],ry=np.arctan2(reflected[0],reflected[2])),nsq.RayDatabaseConfig(4,4))
    if not mirror:
        scene.add_detector('transmitted',CS(z=20),nsq.RayDatabaseConfig(4,4))
    return scene,reflected


def trace_branches(bridge, stack, nm, angle=45., mirror=False, count=4096):
    r,t=rt(bridge,stack,nm,angle)
    scene,direction=branch_scene(float(r[0]),float(t[0]),nm,angle,mirror)
    result=scene.trace(num_rays=count,max_depth=4,seed=2026,record_paths=128)
    budget=ledger(result)
    budget['coating_loss']=float(1-r[0] if mirror else 1-r[0]-t[0])
    budget['accounted_residual']=abs(budget['total_flux_in']-sum(budget[k] for k in ('total_flux_detected','total_flux_absorbed','total_flux_bulk_absorbed','total_flux_escaped','total_flux_lost','coating_loss')))
    rays=result.detectors['reflected']
    actual=np.column_stack([rays.L,rays.M,rays.N])
    error=float(np.max(np.abs(actual-direction))) if len(actual) else None
    normal=np.array([np.sin(np.deg2rad(angle)),0,np.cos(np.deg2rad(angle))])
    paths=[]
    for name,det in result.detectors.items():
        for j in range(min(24,len(det.x))):
            point=np.array([det.x[j],det.y[j],det.z[j]])
            ray_direction=np.array([det.L[j],det.M[j],det.N[j]])
            distance=np.dot(point,normal)/np.dot(ray_direction,normal)
            hit=point-distance*ray_direction
            paths.append({'branch':name,'xyz':[[float(hit[0]),float(hit[1]),-10.],hit.tolist(),point.tolist()]})
    return dict(expected_R=float(r[0]),expected_T=float(t[0]),reflected_flux=rays.total_flux,
                transmitted_flux=result.detectors['transmitted'].total_flux if not mirror else None,
                reflection_direction=direction.tolist(),direction_error=error,ledger=budget,
                events=result.ray_paths['events'],paths=paths,mode='opaque_mirror' if mirror else 'effective_thin_splitter',angle_deg=angle,wavelength_nm=nm)


class FilmSurface(nsq.RefractiveComponent):
    """Update coating power for incidence direction and angular bin per ray."""
    def __init__(self,*args,bridge,stack,nm,counts,angle_step=.5,**kwargs):
        super().__init__(*args,**kwargs)
        self.counts=counts
        self.step=angle_step
        angles=np.arange(0,90+angle_step/2,angle_step)
        angles=np.minimum(angles,89.999)
        reverse=CoatingStackInput(stack.substrate_material_id,stack.incident_material_id,tuple(reversed(stack.layers)))
        self.tables=[rt(bridge,s,nm,angles) for s in (stack,reverse)]

    def interact(self,rays,t,normals,hit_mask,rng,bsdf_ir,n_geom,sampling=None,forced_branch=None):
        # Backend lowering preserves this component; branch sampling remains
        # native Optiland. Only its scalar coating is set for each angle bin.
        directions=np.column_stack([rays.L,rays.M,rays.N])
        dot=np.sum(directions*np.asarray(n_geom),axis=1)
        angles=np.rad2deg(np.arccos(np.clip(np.abs(dot),0,1)))
        bins=np.minimum(np.rint(angles/self.step).astype(int),len(self.tables[0][0])-1)
        keys=bins+ (dot<0)*len(self.tables[0][0])
        hit=np.asarray(hit_mask,dtype=bool)
        for key in np.unique(keys[hit]):
            mask=hit & (keys==key)
            side,index=divmod(int(key),len(self.tables[0][0]))
            r,tv=(float(table[index]) for table in self.tables[side])
            r=float(np.clip(r,0,1)); tv=float(np.clip(tv,0,1-r))
            self.coating=SimpleCoating(reflectance=r,transmittance=tv)
            super().interact(rays,t,normals,mask,rng,bsdf_ir,n_geom,sampling,forced_branch)
        after=np.sum(np.column_stack([rays.L,rays.M,rays.N])*np.asarray(n_geom),axis=1)
        for rid in np.asarray(rays.ray_id)[hit & (dot*after<0)]:
            self.counts[int(rid)]=self.counts.get(int(rid),0)+1
        self.coating=None


def matched_scene(bridge,spec,optic,nm,angle_step=.5):
    if spec.surfaces[0].material_id!='Air':
        raise ValueError('匹配鬼像目前限于空气中的同轴透镜。')
    scene=nsq.NSQScene()
    scene.sampling_policy=SamplingPolicy(reflect_prob=.1,rr_start_flux=0)
    counts={}; geometry=[]
    # Use actual sequential semi-apertures after trace/draw, and the focused
    # coordinate of every surface. Do not infer lens geometry from its name.
    optic.trace(Hx=0,Hy=1 if spec.field_y_deg else 0,wavelength=nm/1000,num_rays=16)
    for i,s in enumerate(spec.surfaces[1:-1],start=1):
        native=optic.surfaces[i]
        aperture=float(native.aperture.r_max)
        if not np.isfinite(aperture) or aperture<=0:
            raise ValueError(f'面 {i} 缺少有效口径')
        z=float(native.geometry.cs.z)
        radius=s.radius_mm if s.radius_mm is not None else np.inf
        stack=s.coating or CoatingStackInput(spec.surfaces[i-1].material_id,s.material_id)
        front=nsq.NSQMaterial() if spec.surfaces[i-1].material_id=='Air' else nsq.NSQMaterial(bridge.material(spec.surfaces[i-1].material_id))
        back=nsq.NSQMaterial() if s.material_id=='Air' else nsq.NSQMaterial(bridge.material(s.material_id))
        scene.add_component(f'surface_{i}',FilmSurface(CS(z=z),nsq.ConicGeometry(radius,0,aperture),
            front,back,
            bridge=bridge,stack=stack,nm=nm,counts=counts,angle_step=angle_step,name=f'surface_{i}'))
        geometry.append(dict(index=i,z_mm=z,radius_mm=s.radius_mm,aperture_radius_mm=aperture,material=s.material_id))
    # Close each air/glass/air element with its absorbing physical rim.
    from optiland.nonsequential.components.lens import Lens
    for i in range(1,len(spec.surfaces)-2):
        front_spec,back_spec=spec.surfaces[i:i+2]
        if spec.surfaces[i-1].material_id=='Air' and front_spec.material_id!='Air' and back_spec.material_id=='Air':
            front_geo,back_geo=geometry[i-1:i+1]
            rim=Lens(f'edge_{i}',CS(z=front_geo['z_mm']),nsq.LensConfig(
                r1=front_spec.radius_mm or np.inf,r2=back_spec.radius_mm or np.inf,
                thickness=back_geo['z_mm']-front_geo['z_mm'],material=nsq.NSQMaterial(bridge.material(front_spec.material_id)),
                front_aperture_radius=front_geo['aperture_radius_mm'],back_aperture_radius=back_geo['aperture_radius_mm']))
            for j,side in enumerate(rim.surfaces[2:]):
                scene.add_component(f'edge_{i}_{j}',side)
    first_z=geometry[0]['z_mm']
    angle=np.deg2rad(spec.field_y_deg)
    # Rotate about x so the beam follows +y field and centres on entrance stop.
    scene.add_source('source',CS(y=-10*np.tan(angle),z=first_z-10,rx=-angle),
        nsq.CollimatedSourceConfig(nsq.Spectrum.monochromatic(nm/1000),aperture_radius=spec.aperture_epd_mm/2))
    detector_z=float(optic.surfaces[-1].geometry.cs.z)
    scene.add_detector('image',CS(z=detector_z),nsq.RayDatabaseConfig(40,40))
    scene.detectors[-1].name='image'
    return scene,counts,dict(surfaces=geometry,detector_z_mm=detector_z,detector_width_mm=40,field_deg=spec.field_y_deg,epd_mm=spec.aperture_epd_mm,angle_bin_deg=angle_step)


def trace_matched_ghost(bridge,spec,optic,nm,count=40000,depth=24,seed=2026,angle_step=.5):
    scene,counts,geometry=matched_scene(bridge,spec,optic,nm,angle_step)
    result=scene.trace(num_rays=count,max_depth=depth,seed=seed,record_paths=count)
    events=result.ray_paths['events']
    detected=events[(events['event_type']=='hit')&(events['component_name']=='image')]
    ghost=np.array([counts.get(int(rid),0)>0 for rid in detected['ray_id']],dtype=bool)
    total=float(detected['flux'].sum()); ghost_flux=float(detected['flux'][ghost].sum())
    ghost_se=float(np.sqrt(max(np.sum(detected['flux'][ghost]**2)-ghost_flux**2/count,0)))
    total_se=float(np.sqrt(max(np.sum(detected['flux']**2)-total**2/count,0)))
    assert abs(total-result.detectors['image'].total_flux)<1e-10
    grid,_,_=np.histogram2d(detected['y'][ghost],detected['x'][ghost],bins=96,range=[[-20,20],[-20,20]],weights=detected['flux'][ghost])
    return dict(direct_flux=total-ghost_flux,full_flux=total,ghost_flux=ghost_flux,ghost_fraction=ghost_flux/max(total,1e-15),
                ghost_map=grid/(40/96)**2,flux_conservation_error=result.flux_conservation_error,
                recorded_path_events=len(events),geometry=geometry,ledger=ledger(result),ray_count=count,depth=depth,seed=seed,
                detected_ghost_paths=int(ghost.sum()),ghost_flux_standard_error=ghost_se,total_flux_standard_error=total_se)


def render_branch_result(bridge,stack,draft,output_dir):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from experiments.optiland_poc import _json_ready
    output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    mirror=draft['system_template']!='dual_path_beamsplitter'
    nm=float(draft.get('probe_wavelength_nm',550))
    angle=float(draft.get('angle_deg',45))
    if not 0<=angle<=60:
        raise ValueError('反射/分光基线目前支持 0–60° 入射。')
    bare_stack=CoatingStackInput(stack.incident_material_id,stack.substrate_material_id)
    bare=trace_branches(bridge,bare_stack,nm,angle,mirror)
    coated=trace_branches(bridge,stack,nm,angle,mirror)
    artifacts={}
    tilt=np.deg2rad(angle)
    normal=np.array([np.sin(tilt),0,np.cos(tilt)])
    tangent=np.array([np.cos(tilt),0,-np.sin(tilt)])
    vertical=np.array([0.,1.,0.])
    split_half_size=3.2
    splitter_corners=[a*tangent+b*vertical for a,b in ((-split_half_size,-split_half_size),(split_half_size,-split_half_size),(split_half_size,split_half_size),(-split_half_size,split_half_size))]

    def detector_patch(center, direction, half_size=2.2):
        direction=np.asarray(direction,dtype=float)
        side=np.cross(vertical,direction)
        side=side/max(np.linalg.norm(side),1e-12)
        return [center+a*side+b*vertical for a,b in ((-half_size,-half_size),(half_size,-half_size),(half_size,half_size),(-half_size,half_size))]

    reflected_direction=np.asarray(coated['reflection_direction'],dtype=float)
    detector_specs=[('反射探测器',20*reflected_direction,reflected_direction,'#dc2626')]
    if not mirror:
        detector_specs.append(('透射探测器',np.array([0.,0.,20.]),np.array([0.,0.,1.]),'#2563eb'))

    for key,three in (('layout_system',False),('system3d_system',True)):
        fig=plt.figure(figsize=(8.2,5.2)); ax=fig.add_subplot(111,projection='3d' if three else None)
        incident_paths=[path for path in coated['paths'] if path['branch']==('reflected' if mirror else 'transmitted')]
        for path in incident_paths:
            ray=np.asarray(path['xyz'])
            if three: ax.plot(ray[:2,2],ray[:2,0],ray[:2,1],alpha=.28,linewidth=.8,color='#64748b')
            else: ax.plot(ray[:2,2],ray[:2,0],alpha=.28,linewidth=.8,color='#64748b')
        for path in coated['paths']:
            ray=np.asarray(path['xyz']); color='#dc2626' if path['branch']=='reflected' else '#2563eb'
            if three: ax.plot(ray[1:,2],ray[1:,0],ray[1:,1],alpha=.35,linewidth=.85,color=color)
            else: ax.plot(ray[1:,2],ray[1:,0],alpha=.35,linewidth=.85,color=color)
        if three:
            ax.add_collection3d(Poly3DCollection([[p[[2,0,1]] for p in splitter_corners]],facecolors='#14b8a6',edgecolors='#0f172a',linewidths=1.5,alpha=.32))
            for label,center,direction,color in detector_specs:
                corners=detector_patch(center,direction)
                ax.add_collection3d(Poly3DCollection([[p[[2,0,1]] for p in corners]],facecolors=color,edgecolors=color,linewidths=1.2,alpha=.18))
                ax.text(center[2],center[0],center[1]+2.8,label,color=color,fontsize=8,ha='center')
            ax.text(-10,0,3.5,'准直光源',color='#475569',fontsize=8,ha='center')
        else:
            edge=np.asarray([splitter_corners[0],splitter_corners[1]])
            ax.plot(edge[:,2],edge[:,0],color='#0f766e',linewidth=9,alpha=.25)
            ax.plot(edge[:,2],edge[:,0],color='#0f172a',linewidth=2)
            ax.annotate('镜面' if mirror else '等效分光面',xy=(0,0),xytext=(8,10),textcoords='offset points',fontsize=8,fontweight='bold')
            for label,center,direction,color in detector_specs:
                corners=np.asarray(detector_patch(center,direction))
                ax.plot(corners[:2,2],corners[:2,0],color=color,linewidth=6,alpha=.35)
                ax.annotate(label,xy=(center[2],center[0]),xytext=(5,7),textcoords='offset points',color=color,fontsize=8,fontweight='bold')
            ax.annotate('准直光源',xy=(-10,0),xytext=(-30,10),textcoords='offset points',color='#475569',fontsize=8)
            legend=[Line2D([0],[0],color='#64748b',label='入射光'),Line2D([0],[0],color='#dc2626',label=f"反射支路 {coated['reflected_flux']:.3f} W"),Line2D([0],[0],color='#0f172a',linewidth=3,label='镜面' if mirror else '分光面')]
            if not mirror: legend.insert(2,Line2D([0],[0],color='#2563eb',label=f"透射支路 {coated['transmitted_flux']:.3f} W"))
            ax.legend(handles=legend,fontsize=8,loc='upper left')
        ax.set_xlabel('Z (mm)'); ax.set_ylabel('X (mm)')
        if three: ax.set_zlabel('Y (mm)')
        ax.set_title(('单镜反射光路' if mirror else '分光膜反射 / 透射双支路')+f' · {nm:.0f} nm · {angle:.0f}°')
        if not three:
            ax.set_aspect('equal'); ax.grid(alpha=.2)
            ax.text(.99,.03,'功率以 1 W 入射光归一化',transform=ax.transAxes,ha='right',va='bottom',fontsize=8,color='#64748b')
        p=output_dir/f'{key}.png';fig.tight_layout();fig.savefig(p,dpi=160);plt.close(fig);artifacts[key]=str(p)
    fig,ax=plt.subplots(figsize=(7,4))
    keys=['reflected_flux'] if mirror else ['reflected_flux','transmitted_flux']
    x=np.arange(len(keys))
    ax.bar(x-.17,[bare[k] for k in keys],.34,label='裸界面')
    ax.bar(x+.17,[coated[k] for k in keys],.34,label='当前镀膜')
    ax.set_xticks(x,['反射接收功率'] if mirror else ['反射接收功率','透射接收功率'])
    ax.set_ylabel('功率 / W（入射 1 W）');ax.set_ylim(0,1.05);ax.legend()
    p=output_dir/'branch_system.png';fig.tight_layout();fig.savefig(p,dpi=160);plt.close(fig);artifacts['branch_system']=str(p)
    result={'draft':draft,'system_template':draft['system_template'],'system_family':'reflector' if mirror else 'beamsplitter',
            'artifacts':artifacts,'metrics':{},'analysis_conditions':{'wavelength_nm':nm,'field_deg':angle},
            'branch_analysis':{ 'bare':{k:v for k,v in bare.items() if k!='events'},'coated':{k:v for k,v in coated.items() if k!='events'},
                'scope':'单个不透明平面镜；1−R 计为未反射损失，不代表腔反馈或纯吸收。' if mirror else '空气中零厚度等效分光面；以膜系 R/T 分配双支路功率，不包含基片厚度与出射面。'}}
    path=output_dir/'comparison_result.json';path.write_text(json.dumps(_json_ready(result),ensure_ascii=False,indent=2),encoding='utf8')
    return path
