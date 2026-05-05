"""Generic CSV and COMSOL table I/O helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


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
    encodings = ["utf-8-sig", "utf-8", "gbk", "cp936", "ansi", "latin1"]
    last_error = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise UnicodeDecodeError(
        "fallback",
        b"",
        0,
        1,
        f"无法用常见编码读取文件: {path}. 最后错误: {last_error}",
    )


def _read_csv_with_fallback(path: Path, **kwargs) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "gbk", "cp936", "latin1"]
    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise ValueError(f"无法用常见编码读取 CSV: {path}. 最后错误: {last_error}")


def _extract_comment_lines(lines: Sequence[str]) -> List[str]:
    return [line.strip() for line in lines if line.strip().startswith("%")]


def _extract_header_candidates_from_comments(comment_lines: Sequence[str]) -> List[str]:
    for line in reversed(comment_lines):
        text = line.lstrip("%").strip()
        parts = [p.strip().strip('"') for p in text.split(",")]
        if len(parts) < 2:
            continue
        joined = ",".join(parts).lower()
        if any(
            key in joined
            for key in [
                "lambda",
                "wavelength",
                "freq",
                "reflect",
                "trans",
                "abs(",
                "thz",
                "反射",
                "透射",
                "吸收",
                "(m)",
                "nm",
            ]
        ):
            return parts
    return []


def _normalize_label(label: str) -> str:
    return str(label).strip().strip('"').lower()


def _guess_y_kind(y_label: str, y_values: np.ndarray) -> str:
    label = _normalize_label(y_label)
    if "reflect" in label or "反射" in label or label in {"r", "refl"}:
        return "reflectance"
    if "trans" in label or "透射" in label:
        return "transmittance"
    if "abs" in label or "吸收" in label:
        return "absorptance"
    if "freq" in label or "thz" in label or "hz" in label:
        return "frequency"

    y_min = float(np.nanmin(y_values))
    y_max = float(np.nanmax(y_values))
    if y_min >= -0.05 and y_max <= 1.2:
        return "reflectance"
    if y_max > 10:
        return "frequency"
    return "unknown"


def _convert_x_to_nm(x_values: np.ndarray, x_label: str) -> np.ndarray:
    label = _normalize_label(x_label)
    if "wavelength_nm" in label or label == "wavelength_nm" or "nm" in label:
        return x_values.astype(float)
    if "(m)" in label or "lambda0" in label or "lam" in label or "wavelength" in label:
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
            mag_text, _ = text.split("∠", 1)
            return float(mag_text.strip())
        except Exception:
            pass

    alt = text.replace("ЁЯ", "∠").replace("Ёу", "°")
    if "∠" in alt:
        try:
            mag_text, _ = alt.split("∠", 1)
            return float(mag_text.strip())
        except Exception:
            pass

    complex_text = text.replace("i", "j").replace("I", "j")
    try:
        return float(abs(complex(complex_text)))
    except Exception:
        return np.nan


def _clean_numeric_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df_num = df.map(_parse_comsol_value)
    except AttributeError:  # pragma: no cover - compatibility path
        df_num = df.applymap(_parse_comsol_value)
    return df_num.dropna(how="all")


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
    labels: List[str] = []
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
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    text_lines = _read_text_with_fallback(path).splitlines()
    comment_lines = _extract_comment_lines(text_lines)
    standard = _load_standard_csv_with_headers(path)
    if standard is not None:
        data_table, labels = standard
    else:
        data_table, labels = _load_comsol_numeric_table(path, comment_lines)

    x_idx = _pick_column_index(labels, x_selector, default_index=0)
    y_idx = _pick_column_index(labels, y_selector, default_index=1)

    x = data_table.iloc[:, x_idx].to_numpy(dtype=float)
    y = data_table.iloc[:, y_idx].to_numpy(dtype=float)
    finite_mask = np.isfinite(x) & np.isfinite(y)
    x = x[finite_mask]
    y = y[finite_mask]
    if len(x) < 2:
        raise ValueError(f"有效数值点不足: {path}")

    x_label = labels[x_idx]
    y_label = labels[y_idx]
    x_nm = _convert_x_to_nm(x, x_label)
    y_kind = _guess_y_kind(y_label, y)

    order = np.argsort(x_nm)
    x_nm = x_nm[order]
    y = y[order]
    data_table = data_table.iloc[np.where(finite_mask)[0]].reset_index(drop=True)
    data_table = data_table.iloc[order].reset_index(drop=True)

    return SpectrumData(
        path=path,
        x_nm=x_nm.astype(float),
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
            f"文件 {path} 的目标列不是反射率。"
            f" 检测到 y_label='{spec.y_label}', y_kind='{spec.y_kind}'."
        )
    y_min = float(np.nanmin(spec.y))
    y_max = float(np.nanmax(spec.y))
    if y_min < -0.1 or y_max > 1.5:
        raise ValueError(f"文件 {path} 的反射率范围异常: [{y_min:.6f}, {y_max:.6f}]。")
    return spec.x_nm, spec.y


def load_reflectance_spec(
    path: Path,
    y_selector: Optional[Union[int, str]] = None,
) -> SpectrumData:
    spec = load_spectrum_csv(path, y_selector=y_selector)
    if spec.y_kind != "reflectance":
        raise ValueError(
            f"File {path} does not contain a reflectance column. "
            f"Detected y_label='{spec.y_label}', y_kind='{spec.y_kind}'."
        )
    y_min = float(np.nanmin(spec.y))
    y_max = float(np.nanmax(spec.y))
    if y_min < -0.1 or y_max > 1.5:
        raise ValueError(f"File {path} has an invalid reflectance range: [{y_min:.6f}, {y_max:.6f}].")
    return spec
