"""App release scope is explicit; the full catalog remains a developer archive."""
TAMM_TEACHING = {
    'tamm_interface_priority': ('Tamm 教学：Ag/DBR 偏振反射', '比较 p、s 反射谱', '改变 Ag 厚度与 β，对比反射谷的位置，结合相位与场分布判断'),
    'tamm_phase_bundle': ('Tamm 教学：Ag/DBR 反射相位', '理解复反射系数相位随波长的变化', '区分相位主值换支与共振附近的快速变化'),
    'tamm_phase_focus': ('Tamm 教学：Ag/DBR 吸收与场分布', '区分整体吸收率与层内电场强度', '比较吸收谱及独立计算的场分布，观察 Ag 厚度和 DBR 周期数的影响'),
}

APP_CASES = frozenset({
    'quarter_wave_single_layer', 'half_wave_single_layer', 'single_ar',
    'porous_sio2_layer', 'porous_double_ar', 'moth_eye_effective_gradient',
    'double_ar', 'quarter_wave_double_layer', 'triple_ar', 'high_reflector',
    'quarter_wave_stack', 'bragg_reflector', 'fp_single_halfwave', 'fp_filter',
    'fp_double_halfwave', 'narrowband_filter', 'rugate_filter',
    'neutral_beamsplitter', 'guided_grating_emt',
}) | TAMM_TEACHING.keys()


def app_catalog(catalog):
    cases = [case for case in catalog['cases'] if case['case_id'] in APP_CASES]
    cases = [dict(case) for case in cases]
    for case in cases:
        if case['case_id'] not in TAMM_TEACHING:
            continue
        title, goal, task = TAMM_TEACHING[case['case_id']]
        boundary = '当前为 GeneralTmm 平面 Ag/DBR 教学实验，使用保存的常数复折射率。反射、相位、吸收与场分布需联合判断；不能单凭峰谷确认 Tamm 界面态，也不代表历史 COMSOL 端结构或粗糙结构的复现。'
        case.update(title_cn=title, physics_model='GeneralTmm 平面 Ag/DBR（常数复折射率）',
                    structure='Ag / (高折射率层 / 低折射率层)^N / 高折射率层',
                    learning_goal=goal, design_task=task, coating_function='研究金属与介质膜堆的幅相响应和能量分布',
                    application_scene='界面敏感探测与光谱选择的教学原型',
                    review_boundary=boundary, notes=boundary, system_experiment=None,
                    calculation_source='GeneralTmm 在线教学实验',
                    optiland={'enabled': False, 'level': 'none', 'observables': []})
    return {**catalog, 'cases': cases, 'physical_case_count': len(cases),
            'interactive_case_count': sum(c['has_live_simulation'] for c in cases),
            'static_case_count': sum(not c['has_live_simulation'] for c in cases),
            'category_breakdown': {k: sum(c['category'] == k for c in cases) for k in catalog['categories']}}
