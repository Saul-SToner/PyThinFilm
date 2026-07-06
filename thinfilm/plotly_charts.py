"""Interactive Plotly charts for optical thin-film demonstration.

Provides publication-quality interactive visualizations for the
teaching platform and competition demos.

Requires: plotly
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .plot_logic import focused_power_limits, infer_rta_focus, rta_trace_styles

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    raise ImportError("plotly is required: pip install plotly")


# ---------------------------------------------------------------------------
# Color scheme
# ---------------------------------------------------------------------------

COLORS = {
    "R": "#0F4D92",
    "T": "#42949E",
    "A": "#7C6CCF",
    "layer_high": "#7C6CCF",
    "layer_low": "#77D7D1",
    "substrate": "#F2F2F2",
    "incident": "#ffffff",  # White
    "grid": "#E6E6E6",
    "text": "#272727",
    "bg": "#ffffff",
}


def _apply_interactive_style(fig: go.Figure) -> None:
    """Mirror the static semantic palette without treating Plotly as submission art."""
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Arial, Microsoft YaHei, sans-serif", size=12, color=COLORS["text"]),
        title_font=dict(size=16),
        legend=dict(bgcolor="rgba(255,255,255,0)", borderwidth=0),
    )
    fig.update_xaxes(showgrid=False, showline=True, linewidth=1, linecolor="#272727", mirror=False)
    fig.update_yaxes(showgrid=False, showline=True, linewidth=1, linecolor="#272727", mirror=False)


# ---------------------------------------------------------------------------
# 1. R/T/A Spectrum Chart
# ---------------------------------------------------------------------------

def plot_rta_spectrum(
    wavelengths_nm: np.ndarray,
    R: np.ndarray,
    T: np.ndarray,
    A: np.ndarray,
    *,
    title: str = "光学薄膜光谱特性",
    design_type: str | None = None,
    focus: str | None = None,
    focus_view: bool = True,
    show_legend: bool = True,
    height: int = 450,
) -> go.Figure:
    """Create an interactive R/T/A spectrum plot.

    Parameters
    ----------
    wavelengths_nm : array
        Wavelength array in nanometers.
    R, T, A : arrays
        Reflectance, transmittance, absorptance arrays.
    title : str
        Chart title.
    design_type : str, optional
        Design type label to show in subtitle.
    focus : {"R", "T", "A"}, optional
        Explicit primary quantity. If omitted, infer from case semantics/data.
    focus_view : bool
        Start with a tight primary-quantity y range. A button restores the
        complete R/T/A range.
    show_legend : bool
        Whether to show legend.
    height : int
        Chart height in pixels.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    curves = {
        "R": np.asarray(R, dtype=float),
        "T": np.asarray(T, dtype=float),
        "A": np.asarray(A, dtype=float),
    }
    focus_kind = infer_rta_focus(
        curves["R"],
        curves["T"],
        curves["A"],
        context=f"{title} {design_type or ''}",
        preferred=focus,
    )
    trace_styles = rta_trace_styles(focus_kind, curves)
    focus_limits = focused_power_limits(curves[focus_kind])
    focus_cn = {"R": "反射率 R", "T": "透射率 T", "A": "吸收率 A"}[focus_kind]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=wavelengths_nm, y=R,
        name="R (反射率 Reflectance)",
        line=dict(color=COLORS["R"], width=trace_styles["R"]["linewidth"], dash=trace_styles["R"]["dash"]),
        opacity=trace_styles["R"]["alpha"],
        hovertemplate="λ=%{x:.1f} nm<br>R=%{y:.4f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=wavelengths_nm, y=T,
        name="T (透射率 Transmittance)",
        line=dict(color=COLORS["T"], width=trace_styles["T"]["linewidth"], dash=trace_styles["T"]["dash"]),
        opacity=trace_styles["T"]["alpha"],
        hovertemplate="λ=%{x:.1f} nm<br>T=%{y:.4f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=wavelengths_nm, y=A,
        name="A (吸收率 Absorptance)",
        line=dict(color=COLORS["A"], width=trace_styles["A"]["linewidth"], dash=trace_styles["A"]["dash"]),
        opacity=trace_styles["A"]["alpha"],
        hovertemplate="λ=%{x:.1f} nm<br>A=%{y:.4f}<extra></extra>",
    ))

    # Energy conservation line
    total = R + T + A
    if not np.allclose(total, 1.0, atol=0.01):
        fig.add_trace(go.Scatter(
            x=wavelengths_nm, y=total,
            name="R+T+A",
            line=dict(color="#999999", width=1, dash="dash"),
            hovertemplate="λ=%{x:.1f} nm<br>R+T+A=%{y:.4f}<extra></extra>",
        ))

    subtitle_parts = [part for part in (design_type, f"主变量：{focus_cn}") if part]
    subtitle = " · ".join(subtitle_parts)
    initial_range = list(focus_limits) if focus_view else [-0.02, 1.05]

    fig.update_layout(
        title=dict(
            text=f"{title}<br><sub>{subtitle}</sub>" if subtitle else title,
            x=0.02,
            xanchor="left",
        ),
        xaxis_title="波长 (nm)",
        yaxis_title="R / T / A",
        yaxis=dict(range=initial_range),
        showlegend=show_legend,
        legend=dict(
            x=0.01, y=0.99,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=COLORS["grid"],
            borderwidth=1,
        ),
        template="plotly_white",
        height=height,
        hovermode="x unified",
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=1.0,
                xanchor="right",
                y=1.16,
                yanchor="top",
                buttons=[
                    dict(label=f"聚焦 {focus_kind}", method="relayout", args=[{"yaxis.range": list(focus_limits)}]),
                    dict(label="R/T/A 总览", method="relayout", args=[{"yaxis.range": [-0.02, 1.05]}]),
                ],
            )
        ],
    )

    _apply_interactive_style(fig)
    return fig


# ---------------------------------------------------------------------------
# 2. Layer Structure Diagram
# ---------------------------------------------------------------------------

def plot_layer_structure(
    layers: List[Dict[str, Any]],
    *,
    n_incident: float = 1.0,
    n_substrate: float = 1.52,
    title: str = "膜层结构示意图",
    height: int = 400,
) -> go.Figure:
    """Create a schematic layer structure diagram.

    Parameters
    ----------
    layers : list of dict
        Each dict has 'name', 'thickness_nm', and optionally 'n' or 'material'.
    n_incident : float
        Incident medium refractive index.
    n_substrate : float
        Substrate refractive index.
    title : str
        Chart title.
    height : int
        Chart height.

    Returns
    -------
    go.Figure
        Plotly figure with colored rectangles for each layer.
    """
    fig = go.Figure()

    # Build layer list with incident and substrate
    all_layers = [{"name": "入射介质", "thickness_nm": 0, "n": n_incident, "is_halfspace": True}]
    all_layers.extend(layers)
    all_layers.append({"name": "基底", "thickness_nm": 0, "n": n_substrate, "is_halfspace": True})

    # Calculate positions
    total_thickness = sum(float(l.get("thickness_nm", 0)) for l in layers)
    scale = max(total_thickness, 100) / 10  # Normalize to reasonable width

    x_left = 0
    colors = [COLORS["incident"], COLORS["substrate"]]
    layer_colors = [COLORS["layer_high"], COLORS["layer_low"]]
    label_stride = max(1, int(np.ceil(len(layers) / 8)))

    for i, layer in enumerate(all_layers):
        if layer.get("is_halfspace"):
            # Half-space: draw wide rectangle
            width = scale * 2
            if i == 0:
                x = -width
            else:
                x = total_thickness
            color = colors[i % 2]
            fig.add_shape(
                type="rect",
                x0=x, x1=x + width,
                y0=0, y1=1,
                fillcolor=color,
                opacity=0.3,
                line=dict(width=1, color=COLORS["grid"]),
            )
            fig.add_annotation(
                x=x + width / 2, y=0.5,
                text=f"{layer['name']}<br>n={layer.get('n', '?'):.2f}",
                showarrow=False,
                font=dict(size=10, color=COLORS["text"]),
            )
        else:
            # Regular layer
            thickness = float(layer.get("thickness_nm", 0))
            n_val = layer.get("n", layer.get("n_real", 1.5))
            color = layer_colors[i % 2]

            fig.add_shape(
                type="rect",
                x0=x_left, x1=x_left + thickness,
                y0=0, y1=1,
                fillcolor=color,
                opacity=0.6,
                line=dict(width=2, color=color),
            )

            layer_index = i - 1
            if len(layers) <= 8 or layer_index % label_stride == 0 or layer_index == len(layers) - 1:
                label = f"{layer['name']}<br>{thickness:.0f} nm · n={n_val:.2f}"
                fig.add_annotation(
                    x=x_left + thickness / 2, y=0.5,
                    text=label,
                    showarrow=False,
                    font=dict(size=9, color="white"),
                )

            x_left += thickness

    fig.update_layout(
        title=f"{title}<br><sub>{len(layers)} 层 · 总厚度 {total_thickness:.0f} nm；仅标注代表层</sub>" if len(layers) > 8 else title,
        xaxis=dict(
            title="位置 (nm)",
            range=[-scale * 2.5, total_thickness + scale * 2.5],
            showgrid=False,
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            range=[-0.1, 1.1],
        ),
        template="plotly_white",
        height=height,
        plot_bgcolor=COLORS["bg"],
    )

    _apply_interactive_style(fig)
    return fig


# ---------------------------------------------------------------------------
# 3. Angle Dependence 3D Surface
# ---------------------------------------------------------------------------

def plot_angle_wavelength_surface(
    wavelengths_nm: np.ndarray,
    angles_deg: np.ndarray,
    R_2d: np.ndarray,
    *,
    title: str = "角度–波长响应图",
    quantity: str = "R",
    render_mode: str = "heatmap",
    height: int = 500,
) -> go.Figure:
    """Create a quantitative heatmap, with an optional 3D exploratory view.

    Parameters
    ----------
    wavelengths_nm : array
        1D wavelength array.
    angles_deg : array
        1D angle array.
    R_2d : 2D array
        Shape (len(angles), len(wavelengths)).
    title : str
        Chart title.
    quantity : str
        "R", "T", or "A".
    height : int
        Chart height.

    Returns
    -------
    go.Figure
        3D surface plot.
    """
    mode = str(render_mode).strip().lower()
    colorscale = "RdBu_r" if quantity == "R" else "Viridis"
    if mode == "heatmap":
        fig = go.Figure(data=[go.Heatmap(
            x=wavelengths_nm, y=angles_deg, z=R_2d,
            colorscale=colorscale, colorbar=dict(title=quantity),
            hovertemplate="λ=%{x:.1f} nm<br>θ=%{y:.1f}°<br>" + quantity + "=%{z:.4f}<extra></extra>",
        )])
        fig.update_layout(
            title=title, xaxis_title="波长 (nm)", yaxis_title="入射角 (°)",
            template="plotly_white", height=height,
        )
    elif mode == "surface":
        fig = go.Figure(data=[go.Surface(
            x=wavelengths_nm, y=angles_deg, z=R_2d,
            colorscale=colorscale, colorbar=dict(title=quantity),
        )])
        fig.update_layout(
            title=f"{title}（探索视图）",
            scene=dict(xaxis_title="波长 (nm)", yaxis_title="入射角 (°)", zaxis_title=quantity),
            template="plotly_white", height=height,
        )
    else:
        raise ValueError("render_mode must be 'heatmap' or 'surface'")

    _apply_interactive_style(fig)
    return fig


# ---------------------------------------------------------------------------
# 4. Electric Field Distribution Heatmap
# ---------------------------------------------------------------------------

def plot_field_distribution(
    wavelengths_nm: np.ndarray,
    positions_nm: np.ndarray,
    field_2d: np.ndarray,
    *,
    title: str = "电场强度分布",
    quantity: str = "|E|²",
    height: int = 450,
) -> go.Figure:
    """Create a heatmap of electric field distribution.

    Parameters
    ----------
    wavelengths_nm : array
        1D wavelength array.
    positions_nm : array
        1D position array (depth into structure).
    field_2d : 2D array
        Shape (len(positions), len(wavelengths)).
    title : str
        Chart title.
    quantity : str
        Label for colorbar.
    height : int
        Chart height.

    Returns
    -------
    go.Figure
        Heatmap plot.
    """
    fig = go.Figure(data=[
        go.Heatmap(
            x=wavelengths_nm,
            y=positions_nm,
            z=field_2d,
            colorscale="Hot",
            colorbar=dict(title=quantity),
        )
    ])

    fig.update_layout(
        title=title,
        xaxis_title="波长 (nm)",
        yaxis_title="位置 (nm)",
        template="plotly_white",
        height=height,
    )

    _apply_interactive_style(fig)
    return fig


# ---------------------------------------------------------------------------
# 5. Convergence Plot
# ---------------------------------------------------------------------------

def plot_convergence(
    orders: List[int],
    R_values: List[float],
    *,
    title: str = "近似模型数值稳定性检查",
    height: int = 350,
) -> go.Figure:
    """Plot an order-parameter stability check for the approximate model.

    Parameters
    ----------
    orders : list
        Number of diffraction orders.
    R_values : list
        Zeroth-order reflectance for each order count.
    title : str
        Chart title.
    height : int
        Chart height.

    Returns
    -------
    go.Figure
        Line plot with markers.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=orders, y=R_values,
        mode="lines+markers",
        name="R₀",
        line=dict(color=COLORS["R"], width=2),
        marker=dict(size=8),
        hovertemplate="N=%{x}<br>R₀=%{y:.6f}<extra></extra>",
    ))

    # Convergence band
    if len(R_values) >= 3:
        R_final = R_values[-1]
        fig.add_hline(
            y=R_final,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"收敛值: {R_final:.6f}",
            annotation_position="bottom right",
        )

    fig.update_layout(
        title=title,
        xaxis_title="近似阶数参数 N",
        yaxis_title="零阶反射率 R₀",
        template="plotly_white",
        height=height,
    )
    fig.add_annotation(
        text="用于数值稳定性检查，不代表严格 RCWA 收敛性证明",
        x=0.01, y=0.01, xref="paper", yref="paper",
        showarrow=False, font=dict(size=11, color="#65727A"),
        xanchor="left", yanchor="bottom",
    )

    _apply_interactive_style(fig)
    return fig


# ---------------------------------------------------------------------------
# 6. Multi-design Comparison
# ---------------------------------------------------------------------------

def plot_design_comparison(
    designs: Dict[str, Dict[str, Any]],
    *,
    title: str = "多设计对比",
    quantity: str = "R",
    height: int = 450,
) -> go.Figure:
    """Compare multiple designs on the same plot.

    Parameters
    ----------
    designs : dict
        Keys are design names, values are dicts with 'wavelength_nm' and quantity.
    title : str
        Chart title.
    quantity : str
        "R", "T", or "A".
    height : int
        Chart height.

    Returns
    -------
    go.Figure
        Multi-line plot.
    """
    fig = go.Figure()

    colors = [COLORS["R"], COLORS["T"], COLORS["A"], "#77D7D1", "#B64342", "#A8A8A8"]

    all_values: list[float] = []
    for i, (name, data) in enumerate(designs.items()):
        wl = data.get("wavelength_nm", data.get("wavelengths_nm", []))
        vals = data.get(quantity, data.get(f"{quantity}_values", []))
        all_values.extend(np.asarray(vals, dtype=float).reshape(-1).tolist())
        color = colors[i % len(colors)]

        fig.add_trace(go.Scatter(
            x=wl, y=vals,
            name=name,
            line=dict(color=color, width=2),
            hovertemplate=f"{name}<br>λ=%{{x:.1f}} nm<br>{quantity}=%{{y:.4f}}<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="波长 (nm)",
        yaxis_title=quantity,
        yaxis=dict(range=list(focused_power_limits(all_values))),
        legend=dict(
            x=0.01, y=0.99,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        template="plotly_white",
        height=height,
        hovermode="x unified",
    )
    fig.update_layout(updatemenus=[dict(
        type="buttons", direction="right", x=1.0, xanchor="right", y=1.14,
        buttons=[
            dict(label=f"聚焦 {quantity}", method="relayout", args=[{"yaxis.range": list(focused_power_limits(all_values))}]),
            dict(label="完整 0–1", method="relayout", args=[{"yaxis.range": [-0.02, 1.05]}]),
        ],
    )])

    _apply_interactive_style(fig)
    return fig


# ---------------------------------------------------------------------------
# 7. Metrics Dashboard
# ---------------------------------------------------------------------------

def plot_pdrc_dashboard(
    lambda_um: np.ndarray,
    R: np.ndarray,
    T: np.ndarray,
    A: np.ndarray,
    metrics: Dict[str, float],
    *,
    title: str = "PDRC 光谱仪表盘",
    height: int = 500,
) -> go.Figure:
    """Create a PDRC-specific dashboard with spectrum and metrics.

    Parameters
    ----------
    lambda_um : array
        Wavelength in micrometers.
    R, T, A : arrays
        Reflectance, transmittance, absorptance.
    metrics : dict
        Contains A_solar_avg, epsilon_8_13_avg, cooling_score.
    title : str
        Chart title.
    height : int
        Chart height.

    Returns
    -------
    go.Figure
        Subplot with spectrum and metrics annotation.
    """
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.7, 0.3],
        specs=[[{"type": "xy"}, {"type": "table"}]],
    )

    # Spectrum
    fig.add_trace(go.Scatter(
        x=lambda_um, y=R,
        name="R", line=dict(color=COLORS["R"], width=2),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=lambda_um, y=T,
        name="T", line=dict(color=COLORS["T"], width=2),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=lambda_um, y=A,
        name="A (ε)", line=dict(color=COLORS["A"], width=2, dash="dot"),
    ), row=1, col=1)

    # Highlight solar and atmospheric window bands
    fig.add_vrect(x0=0.3, x1=2.5, fillcolor="yellow", opacity=0.1,
                  line_width=0, row=1, col=1, annotation_text="太阳波段")
    fig.add_vrect(x0=8.0, x1=13.0, fillcolor="cyan", opacity=0.1,
                  line_width=0, row=1, col=1, annotation_text="大气窗口")

    # Metrics table
    fig.add_trace(go.Table(
        header=dict(
            values=["指标", "数值"],
            fill_color=COLORS["layer_low"],
            font=dict(size=12),
        ),
        cells=dict(
            values=[
                ["A_solar", "ε_8-13μm", "冷却评分"],
                [
                    f"{metrics.get('A_solar_avg', 0):.4f}",
                    f"{metrics.get('epsilon_8_13_avg', 0):.4f}",
                    f"{metrics.get('cooling_score', 0):.4f}",
                ],
            ],
            fill_color="white",
            font=dict(size=11),
        ),
    ), row=1, col=2)

    fig.update_layout(
        title=title,
        xaxis_title="波长 (μm)",
        yaxis_title="R / T / A",
        yaxis=dict(range=[-0.02, 1.05]),
        template="plotly_white",
        height=height,
        showlegend=True,
    )
    fig.update_xaxes(title_text="波长 (μm)", row=1, col=1)

    _apply_interactive_style(fig)
    return fig
