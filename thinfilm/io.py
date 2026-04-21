"""CSV and COMSOL table I/O helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import *
from .optics import build_endpoint_blend_curve, unify_two_reflectance_curves


@dataclass
class SpectrumData:
    path: Path
    x_nm: np.ndarray
    y: np.ndarray
    x_label: str
    y_label: str
    y_kind: str
    data_table: pd.DataFrame
    comment_lines: List[str]
    all_column_labels: List[str]

def _read_text_with_fallback(path: Path) -> str:
    """
    按多个常见编码尝试读取文本文件。
    """
    encodings = ["utf-8-sig", "utf-8", "gbk", "cp936", "ansi", "latin1"]

    last_error = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception as e:
            last_error = e

    raise UnicodeDecodeError(
        "fallback",
        b"",
        0,
        1,
        f"无法用常见编码读取文件: {path}. 最后错误: {last_error}",
    )

def _read_csv_with_fallback(path: Path, **kwargs) -> pd.DataFrame:
    """
    按多个常见编码尝试 pandas.read_csv。
    """
    encodings = ["utf-8-sig", "utf-8", "gbk", "cp936", "latin1"]

    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except Exception as e:
            last_error = e

    raise ValueError(f"无法用常见编码读取 CSV: {path}. 最后错误: {last_error}")

def _read_text_lines(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return _read_text_with_fallback(path).splitlines()

def _extract_comment_lines(lines: Sequence[str]) -> List[str]:
    return [line.strip() for line in lines if line.strip().startswith("%")]

def _extract_header_candidates_from_comments(comment_lines: Sequence[str]) -> List[str]:
    """
    尝试从 COMSOL 注释头中提取最后一行列标题。
    常见格式:
        % lambda0 (m),freq (THz),反射率，端口 1 (1)
        % lambda0 (m),R_0deg,R_80deg
    """
    for line in reversed(comment_lines):
        text = line.lstrip("%").strip()
        parts = [p.strip().strip('"') for p in text.split(",")]
        if len(parts) >= 2:
            joined = ",".join(parts).lower()
            looks_like_header = any(
                key in joined
                for key in [
                    "lambda", "wavelength", "freq", "reflect", "thz",
                    "(m)", "nm", "intensity", "trans", "abs(", "反射"
                ]
            )
            if looks_like_header:
                return parts
    return []

def _normalize_label(label: str) -> str:
    return label.strip().strip('"').lower()

def _guess_y_kind(y_label: str, y_values: np.ndarray) -> str:
    label = _normalize_label(y_label)

    if "reflect" in label or "反射" in label or label in {"r", "refl"}:
        return "reflectance"
    if "freq" in label or "thz" in label or "hz" in label:
        return "frequency"
    if "trans" in label or "透射" in label:
        return "transmittance"

    y_min = float(np.nanmin(y_values))
    y_max = float(np.nanmax(y_values))

    if y_min >= -0.05 and y_max <= 1.2:
        return "reflectance"
    if y_max > 10:
        return "frequency"
    return "unknown"

def _convert_x_to_nm(x_values: np.ndarray, x_label: str) -> np.ndarray:
    label = _normalize_label(x_label)

    if "nm" in label:
        return x_values.astype(float)

    if "(m)" in label or label.endswith("_m") or "lambda0" in label or "wavelength" in label:
        if np.nanmax(np.abs(x_values)) < 1e-3:
            return x_values.astype(float) * 1e9

    if np.nanmax(np.abs(x_values)) < 1e-3:
        return x_values.astype(float) * 1e9

    return x_values.astype(float)

def _pick_column_index(
    labels: Sequence[str],
    selector: Optional[Union[int, str]],
    default_index: int = 1,
) -> int:
    n_cols = len(labels)
    if n_cols < 2:
        raise ValueError("数据列数不足。")

    if selector is None:
        return min(default_index, n_cols - 1)

    if isinstance(selector, int):
        if selector < 0 or selector >= n_cols:
            raise IndexError(f"列号越界: selector={selector}, n_cols={n_cols}")
        return selector

    key = _normalize_label(selector)
    for i, lab in enumerate(labels):
        if key in _normalize_label(lab):
            return i

    raise ValueError(f"没有找到匹配列: selector='{selector}', labels={list(labels)}")

def _parse_comsol_value(value) -> float:
    if value is None:
        return np.nan

    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip()
    if text == "":
        return np.nan

    try:
        return float(text)
    except Exception:
        pass

    if "∠" in text:
        try:
            mag_text, ang_text = text.split("∠", 1)
            mag = float(mag_text.strip())
            ang_text = ang_text.strip().replace("°", "")
            ang_deg = float(ang_text)
            real = mag * np.cos(np.deg2rad(ang_deg))
            imag = mag * np.sin(np.deg2rad(ang_deg))
            return float(np.hypot(real, imag))
        except Exception:
            pass

    text_complex = text.replace("i", "j").replace("I", "j")
    try:
        c = complex(text_complex)
        return float(abs(c))
    except Exception:
        pass

    return np.nan

def _clean_numeric_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    兼容不同 pandas 版本：
    - 新版本优先用 DataFrame.map
    - 老版本回退到 DataFrame.applymap
    """
    try:
        df_num = df.map(_parse_comsol_value)
    except AttributeError:
        df_num = df.applymap(_parse_comsol_value)

    df_num = df_num.dropna(how="all")
    return df_num

def _load_standard_csv_with_headers(path: Path) -> Optional[Tuple[pd.DataFrame, List[str]]]:
    try:
        df = _read_csv_with_fallback(path)
    except Exception:
        return None

    if df.shape[1] < 2:
        return None

    df_num = _clean_numeric_dataframe(df)
    if df_num.shape[1] < 2 or len(df_num) < 2:
        return None

    labels = [str(c).strip() for c in df.columns]
    return df_num.reset_index(drop=True), labels

def _load_comsol_numeric_table(path: Path, comment_lines: Sequence[str]) -> Tuple[pd.DataFrame, List[str]]:
    df = _read_csv_with_fallback(path, comment="%", header=None)
    df_num = _clean_numeric_dataframe(df)

    if df_num.shape[1] < 2 or len(df_num) < 2:
        raise ValueError(f"CSV 至少需要两列有效数值数据: {path}")

    header_candidates = _extract_header_candidates_from_comments(comment_lines)

    if len(header_candidates) >= df_num.shape[1]:
        labels = header_candidates[:df_num.shape[1]]
    else:
        labels = []
        for i in range(df_num.shape[1]):
            if i < len(header_candidates):
                labels.append(header_candidates[i])
            else:
                labels.append(f"col_{i}")

    return df_num.reset_index(drop=True), labels

def load_spectrum_csv(
    path: Path,
    y_selector: Optional[Union[int, str]] = None,
    x_selector: Union[int, str] = 0,
) -> SpectrumData:
    """
    通用读取：
    1) 标准 CSV:
         wavelength_nm,reflectance
         400,0.12
         ...
    2) COMSOL 原始导出:
         % Model,...
         % lambda0 (m),freq (THz),反射率，端口 1 (1)
         4.0e-7,749.4,1.685E-2∠0°
         ...
    3) 多列数值表:
         % lambda0 (m),R_0deg,R_80deg
         ...
       通过 y_selector 指定要用哪一列。
    """
    path = Path(path)
    lines = _read_text_lines(path)
    comment_lines = _extract_comment_lines(lines)

    std_result = _load_standard_csv_with_headers(path)
    if std_result is not None:
        data_table, labels = std_result
    else:
        data_table, labels = _load_comsol_numeric_table(path, comment_lines)

    x_idx = _pick_column_index(labels, x_selector, default_index=0)
    y_idx = _pick_column_index(labels, y_selector, default_index=1)

    x_label = labels[x_idx]
    y_label = labels[y_idx]

    x = data_table.iloc[:, x_idx].to_numpy(dtype=float)
    y = data_table.iloc[:, y_idx].to_numpy(dtype=float)

    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    if len(x) < 2:
        raise ValueError(f"有效数值点不足: {path}")

    x_nm = _convert_x_to_nm(x, x_label)
    y_kind = _guess_y_kind(y_label, y)

    return SpectrumData(
        path=path,
        x_nm=x_nm,
        y=y.astype(float),
        x_label=x_label,
        y_label=y_label,
        y_kind=y_kind,
        data_table=data_table.copy(),
        comment_lines=list(comment_lines),
        all_column_labels=list(labels),
    )

def read_reflectance_csv(
    path: Path,
    y_selector: Optional[Union[int, str]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    spec = load_spectrum_csv(path, y_selector=y_selector)

    if spec.y_kind != "reflectance":
        raise ValueError(
            f"文件 {path} 的目标列不是反射率。\n"
            f"检测到 y_label = '{spec.y_label}', y_kind = '{spec.y_kind}'.\n"
            f"如果是多列表，请设置正确的 y_selector；"
            f"如果当前列是 freq/THz，则它不能直接用于膜厚拟合。"
        )

    y_min = float(np.nanmin(spec.y))
    y_max = float(np.nanmax(spec.y))
    if y_min < -0.1 or y_max > 1.5:
        raise ValueError(
            f"文件 {path} 的反射率范围异常: [{y_min:.6f}, {y_max:.6f}]。"
        )

    return spec.x_nm, spec.y

def load_reflectance_spec(
    path: Path,
    y_selector: Optional[Union[int, str]] = None,
) -> SpectrumData:
    spec = load_spectrum_csv(path, y_selector=y_selector)

    if spec.y_kind != "reflectance":
        raise ValueError(
            f"File {path} does not contain a reflectance column for fitting. "
            f"Detected y_label='{spec.y_label}', y_kind='{spec.y_kind}'."
        )

    y_min = float(np.nanmin(spec.y))
    y_max = float(np.nanmax(spec.y))
    if y_min < -0.1 or y_max > 1.5:
        raise ValueError(
            f"File {path} has an invalid reflectance range: [{y_min:.6f}, {y_max:.6f}]."
        )

    return spec

def validate_single_fit_input_theta(
    spec: SpectrumData,
    expected_theta_deg: float,
) -> None:
    theta_deg = extract_constant_theta_deg(spec)
    if theta_deg is not None and abs(theta_deg - expected_theta_deg) > 0.5:
        raise ValueError(
            f"Input angle mismatch for {spec.path.name}: expected about "
            f"{expected_theta_deg:.3f} deg, but the CSV theta column is {theta_deg:.3f} deg."
        )

def extract_constant_theta_deg(spec: SpectrumData) -> Optional[float]:
    for idx, label in enumerate(spec.all_column_labels):
        norm_label = _normalize_label(label)
        if "theta" not in norm_label:
            continue

        values = spec.data_table.iloc[:, idx].to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        if len(values) == 0:
            continue

        value_span = float(np.max(values) - np.min(values))
        value_mid = float(np.median(values))
        if value_span > 1e-6:
            continue

        if np.max(np.abs(values)) <= 2.5 * np.pi:
            return float(np.rad2deg(value_mid))
        return value_mid

    return None

def validate_dual_fit_inputs(
    spec_1: SpectrumData,
    expected_theta_1_deg: float,
    spec_2: SpectrumData,
    expected_theta_2_deg: float,
) -> None:
    validate_single_fit_input_theta(spec_1, expected_theta_1_deg)
    validate_single_fit_input_theta(spec_2, expected_theta_2_deg)

    common_min = max(float(np.min(spec_1.x_nm)), float(np.min(spec_2.x_nm)), LAMBDA_MIN_NM)
    common_max = min(float(np.max(spec_1.x_nm)), float(np.max(spec_2.x_nm)), LAMBDA_MAX_NM)
    if common_max <= common_min:
        return

    grid_nm = np.linspace(common_min, common_max, 200)
    y1 = np.interp(grid_nm, spec_1.x_nm, spec_1.y)
    y2 = np.interp(grid_nm, spec_2.x_nm, spec_2.y)

    rms_diff = float(np.sqrt(np.mean((y1 - y2) ** 2)))
    corr = float(np.corrcoef(y1, y2)[0, 1]) if len(y1) >= 2 else 1.0
    if rms_diff < 1e-5 and corr > 0.9999:
        raise ValueError(
            f"The two fit inputs are nearly identical over {common_min:.1f}-{common_max:.1f} nm "
            f"(RMS diff={rms_diff:.3e}, corr={corr:.6f}). Dual-angle fitting will collapse in this case."
        )

def resolve_dual_fit_curves(
    csv_file_1: Path,
    csv_file_2: Path,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Union[str, float]]]:
    if POL == "mix" and MIX_USE_ENDPOINT_TARGET_BLEND:
        required_paths = {
            "0deg_s": MIX_SOURCE_CSV_0DEG_S,
            "0deg_p": MIX_SOURCE_CSV_0DEG_P,
            "2deg_s": MIX_SOURCE_CSV_2DEG_S,
            "2deg_p": MIX_SOURCE_CSV_2DEG_P,
        }
        missing = [name for name, path in required_paths.items() if path is None]
        if missing:
            raise ValueError(
                "Mixed endpoint blending is enabled, but these source CSV paths are missing: "
                + ", ".join(missing)
            )

        spec_0_s = load_reflectance_spec(Path(MIX_SOURCE_CSV_0DEG_S), y_selector=FIT_Y_SELECTOR_0DEG)
        spec_0_p = load_reflectance_spec(Path(MIX_SOURCE_CSV_0DEG_P), y_selector=FIT_Y_SELECTOR_0DEG)
        spec_2_s = load_reflectance_spec(Path(MIX_SOURCE_CSV_2DEG_S), y_selector=FIT_Y_SELECTOR_2DEG)
        spec_2_p = load_reflectance_spec(Path(MIX_SOURCE_CSV_2DEG_P), y_selector=FIT_Y_SELECTOR_2DEG)

        validate_single_fit_input_theta(spec_0_s, THETA1)
        validate_single_fit_input_theta(spec_0_p, THETA1)
        validate_single_fit_input_theta(spec_2_s, THETA2)
        validate_single_fit_input_theta(spec_2_p, THETA2)

        w1_nm, R1, source_1 = build_endpoint_blend_curve(
            spec_0_s, spec_0_p, MIX_SOURCE_0DEG_MODE, MIX_SOURCE_P_WEIGHT
        )
        w2_nm, R2, source_2 = build_endpoint_blend_curve(
            spec_2_s, spec_2_p, MIX_SOURCE_2DEG_MODE, MIX_SOURCE_P_WEIGHT
        )

        lam_nm, R1_i, R2_i = unify_two_reflectance_curves(
            w1_nm,
            R1,
            w2_nm,
            R2,
            wmin_nm=LAMBDA_MIN_NM,
            wmax_nm=LAMBDA_MAX_NM,
            n_lambda=N_LAMBDA,
        )
        meta: Dict[str, Union[str, float]] = {
            "input_mode": "mix_endpoint_target_blend",
            "curve_1_source": source_1,
            "curve_2_source": source_2,
            "mix_source_p_weight": float(MIX_SOURCE_P_WEIGHT),
            "mix_source_0deg_mode": str(MIX_SOURCE_0DEG_MODE),
            "mix_source_2deg_mode": str(MIX_SOURCE_2DEG_MODE),
        }
        return lam_nm, R1_i, R2_i, meta

    spec_1 = load_reflectance_spec(csv_file_1, y_selector=FIT_Y_SELECTOR_0DEG)
    spec_2 = load_reflectance_spec(csv_file_2, y_selector=FIT_Y_SELECTOR_2DEG)
    validate_dual_fit_inputs(spec_1, THETA1, spec_2, THETA2)

    lam_nm, R1_i, R2_i = unify_two_reflectance_curves(
        spec_1.x_nm,
        spec_1.y,
        spec_2.x_nm,
        spec_2.y,
        wmin_nm=LAMBDA_MIN_NM,
        wmax_nm=LAMBDA_MAX_NM,
        n_lambda=N_LAMBDA,
    )
    meta = {
        "input_mode": "direct_csv",
        "curve_1_source": str(csv_file_1),
        "curve_2_source": str(csv_file_2),
    }
    return lam_nm, R1_i, R2_i, meta

def preview_csv(
    path: Path,
    y_selector: Optional[Union[int, str]] = None,
    save_plot: bool = True,
) -> SpectrumData:
    spec = load_spectrum_csv(path, y_selector=y_selector)

    print("=" * 90)
    print("CSV preview")
    print("=" * 90)
    print(f"path          = {spec.path}")
    print(f"all columns   = {spec.all_column_labels}")
    print(f"x_label       = {spec.x_label}")
    print(f"y_label       = {spec.y_label}")
    print(f"y_kind        = {spec.y_kind}")
    print(f"n_points      = {len(spec.x_nm)}")
    print(f"x range (nm)  = {spec.x_nm.min():.6f} ~ {spec.x_nm.max():.6f}")
    print(f"y range       = {spec.y.min():.6f} ~ {spec.y.max():.6f}")

    preview_df = pd.DataFrame(
        {
            "wavelength_nm": spec.x_nm,
            spec.y_label: spec.y,
        }
    )
    print("\nHead:")
    print(preview_df.head(10).to_string(index=False))

    plt.figure(figsize=(8, 5))
    plt.plot(spec.x_nm, spec.y, linewidth=1.8)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel(spec.y_label)
    plt.title(f"Preview: {spec.path.name}")
    plt.grid(True)
    plt.tight_layout()

    if save_plot:
        out_path = OUTPUT_DIR / f"{spec.path.stem}_preview.png"
        plt.savefig(out_path, dpi=200)
        print(f"Saved plot: {out_path}")

    plt.show()

    lines = [
        "CSV preview summary",
        f"path = {spec.path}",
        f"all_columns = {spec.all_column_labels}",
        f"x_label = {spec.x_label}",
        f"y_label = {spec.y_label}",
        f"y_kind = {spec.y_kind}",
        f"n_points = {len(spec.x_nm)}",
        f"x_range_nm = {spec.x_nm.min():.6f} ~ {spec.x_nm.max():.6f}",
        f"y_range = {spec.y.min():.6f} ~ {spec.y.max():.6f}",
    ]
    save_text_report(f"{spec.path.stem}_preview_summary.txt", lines)

    return spec

def export_clean_csv(
    input_path: Path,
    output_path: Path,
    y_selector: Optional[Union[int, str]] = None,
) -> SpectrumData:
    spec = load_spectrum_csv(input_path, y_selector=y_selector)

    df_out = pd.DataFrame(
        {
            "wavelength_nm": spec.x_nm,
            spec.y_label: spec.y,
        }
    )
    df_out.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved cleaned csv: {output_path}")

    payload = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "all_columns": spec.all_column_labels,
        "x_label": spec.x_label,
        "y_label": spec.y_label,
        "y_kind": spec.y_kind,
        "n_points": int(len(spec.x_nm)),
    }
    save_json_report(f"{output_path.stem}_export_summary.json", payload)
    return spec

