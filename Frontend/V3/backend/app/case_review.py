"""Reviewed display semantics; preserve original spectra and evidence files."""
ENGINEERING = {
    'app_solar_cell_ar': ('常数折射率平面三层膜 TMM', '当前平均反射率高于裸硅基准，未达到宽带减反目标；未计算太阳光谱加权、电学响应或光电转换效率。'),
    'app_wdm_filter': ('1550 nm 平面 F-P 滤光教学模型', '仅验证单片滤光响应；约 11.82 nm 的导出半高宽不能证明满足密集波分复用通道要求。带外衰减不等于完整接收系统串扰。'),
    'app_laser_mirror': ('1064 nm 平面介质高反膜 TMM', '光谱高反射不代表激光损伤阈值、热稳定性或激光腔往返性能已经验证。'),
    'app_phone_lens_ar': ('常数折射率平面三层膜 TMM', '当前平均反射率高于单层基准，未达到改善目标；不是完整手机镜头，未计算像质或系统鬼像。'),
    'app_smart_window': ('WO3/NiO/Ag 固定状态光谱 TMM', '仅有一个固定光学状态，不模拟电致变色切换、温度响应或建筑热平衡。'),
}
RESEARCH = {
    'mat_library_demo': '此处仅显示 MgF2/SiO2 单层减反代表，不代表材料库全部材料的联合结果。',
    'pdrc_cooling_bundle': '历史文件含有效光学常数近似；当前 WPTherml 光谱实验是独立计算，不能由其光谱直接宣称净制冷功率或降温幅度。',
    'absorbing_baseline_template': '当前曲线来自已绑定的仓库外部基线 CSV，不是输入模板自行生成的独立仿真。',
    'absorbing_surface_bundle': '当前曲线来自 COMSOL 粗糙表面证据，不是可重建的逐层平面膜系。',
    'absorbing_surface_gain': '增益仅相对于已绑定的平面基线和粗糙表面输入成立，不外推到其它材料、几何或波段。',
    'absorbing_surface_gain_trend': '六个已有扫描点不能证明连续区间或其它粗糙度定义下严格单调。',
    'rugate_80layer_table': '80 层离散近似不等于连续渐变的精确解；与 COMSOL 的一致性需独立对照。',
    'advanced_ar_bundle': '这是五项 Python/COMSOL 对照汇总，不是一个复杂镜头或单一可编辑膜系。',
    'porous_double_ar_topic_bundle': '当前曲线验证与其它角度、厚度敏感性文件分开解释，不将单谱吻合当作完整制造容差验收。',
}


def review_metadata(case_id):
    if case_id in ENGINEERING:
        model, boundary = ENGINEERING[case_id]
        return {'physics_model': model, 'notes': boundary, 'review_boundary': boundary}
    if case_id.startswith('tamm_'):
        boundary = '历史 COMSOL/相位筛选证据与当前 GeneralTmm 平面 Ag/DBR 教学实验分别解释；当前实验不能复现或替代历史粗糙结构、端结构或二维场结论。'
        return {'notes': boundary, 'review_boundary': boundary}
    if case_id in RESEARCH:
        return {'notes': RESEARCH[case_id], 'review_boundary': RESEARCH[case_id]}
    return {}


def review_cards(case_id, cards, bound=False):
    cards = [dict(card) for card in cards]
    if case_id == 'absorbing_baseline_template' and bound:
        for card in cards:
            if card['label'] == '模板状态': card['value'] = '已绑定外部基线'
    # Replace signed improvement marketing with an explicit percentage-point
    # comparison; don't change the underlying physical result.
    comparisons = {
        'app_solar_cell_ar': ('avg_R_300_1100nm', 'avg_R_bare_Si', 'efficiency_improvement_pct'),
        'app_phone_lens_ar': ('avg_R_visible', 'avg_R_single_layer', 'R_improvement_vs_single'),
    }
    if case_id in comparisons:
        current, baseline, old = comparisons[case_id]
        values = {c['label']: c['value'] for c in cards}
        cards = [c for c in cards if c['label'] != old]
        if all(isinstance(values.get(k), (int,float)) for k in (current,baseline)):
            delta = (values[current]-values[baseline])*100
            cards.insert(0, {'label': '平均反射率较基准变化', 'value': delta, 'unit': '百分点', 'note': '正值表示反射增加，减反表现变差'})
    return cards
