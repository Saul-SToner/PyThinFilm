from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union


# =========================================================
# 0. 运行模式
# =========================================================
# 可选:
#   "preview_csv"                 -> 直接预览单个 CSV（适合 COMSOL 原始导出）
#   "export_clean_csv"            -> 把 COMSOL 原始 CSV 清洗成标准两列 CSV
#   "fit_csv"                     -> 用两条反射率 CSV 做双角度拟合
#   "fit_csv_with_theta2_search"  -> 用两条反射率 CSV 做双角度拟合，并联合搜索第二角
#   "batch_fit_csv"               -> 批量处理文件夹中的成对反射率 CSV
#   "batch_error_analysis"        -> 批量拟合并输出真实厚度误差统计
#   "single_sample_error_analysis"-> 单一样品误差来源分析
#   "theta2_scan_at_fixed_d"      -> 固定厚度，只扫描第二角并比较曲线
#   "fit_csv_compare_pols"   -> 固定厚度下比较指定角度曲线与理论 s/p/avg
#   "single_angle_0deg_scan"      -> 只用 0deg 曲线做厚度扫描
#   "objective_heatmap_d_theta2"  -> 画 objective(d, theta2) 热图

RUN_MODE = "fit_csv_with_theta2_search"

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

CSV_FILE_0DEG = DATA_DIR / "deg.s" / "60nm_10deg_s.csv"
CSV_FILE_2DEG = DATA_DIR / "deg.s" / "60nm_80deg_s.csv"

FIT_Y_SELECTOR_0DEG = "总反射率"
FIT_Y_SELECTOR_2DEG = "总反射率"

N0 = 1.0
N1 = 1.38
N2 = 1.52
USE_DISPERSION = False
DISPERSION_FORM = "cauchy_um"
N1_DISPERSION_B = 0.0
N1_DISPERSION_C = 0.0
N2_DISPERSION_B = 0.0
N2_DISPERSION_C = 0.0

POL = "s"
THETA1 = 10.0
THETA2 = 80.0
THETA2_SEARCH_MIN = -1.0
THETA2_SEARCH_MAX = 1.0
THETA2_SEARCH_STEP = 0.1
MIX_P_WEIGHT = 0.5
FIT_MIX_WEIGHT = False
MIX_WEIGHT_SEARCH_MIN = 0.0
MIX_WEIGHT_SEARCH_MAX = 1.0
MIX_WEIGHT_SEARCH_STEP = 0.05
MIX_USE_ENDPOINT_TARGET_BLEND = True
MIX_SOURCE_P_WEIGHT = 0.6
MIX_SOURCE_0DEG_MODE = "s"
MIX_SOURCE_2DEG_MODE = "blend"
MIX_SOURCE_CSV_0DEG_S: Optional[Path] = DATA_DIR / "deg.s" / "60nm_10deg_s.csv"
MIX_SOURCE_CSV_0DEG_P: Optional[Path] = DATA_DIR / "deg.p" / "60nm_10deg_p.csv"
MIX_SOURCE_CSV_2DEG_S: Optional[Path] = DATA_DIR / "deg.s" / "60nm_80deg_s.csv"
MIX_SOURCE_CSV_2DEG_P: Optional[Path] = DATA_DIR / "deg.p" / "60nm_80deg_p.csv"

# Generic two-angle aliases for future 10deg/80deg workflows.
CSV_FILE_ANGLE1 = CSV_FILE_0DEG
CSV_FILE_ANGLE2 = CSV_FILE_2DEG
FIT_Y_SELECTOR_ANGLE1 = FIT_Y_SELECTOR_0DEG
FIT_Y_SELECTOR_ANGLE2 = FIT_Y_SELECTOR_2DEG
MIX_SOURCE_ANGLE1_MODE = MIX_SOURCE_0DEG_MODE
MIX_SOURCE_ANGLE2_MODE = MIX_SOURCE_2DEG_MODE
MIX_SOURCE_CSV_ANGLE1_S = MIX_SOURCE_CSV_0DEG_S
MIX_SOURCE_CSV_ANGLE1_P = MIX_SOURCE_CSV_0DEG_P
MIX_SOURCE_CSV_ANGLE2_S = MIX_SOURCE_CSV_2DEG_S
MIX_SOURCE_CSV_ANGLE2_P = MIX_SOURCE_CSV_2DEG_P

D_MIN = 5e-9
D_MAX = 300e-9
N_GRID = 1500
N_ITER = 1

LAMBDA_A = 1e6
LAMBDA_B = 1e6

LAMBDA_MIN_NM = 400.0
LAMBDA_MAX_NM = 800.0
N_LAMBDA = 300

USE_THICKNESS_CALIBRATION = False
CAL_A = 1.0
CAL_B = 0.0

SEARCH_METHOD = "multiscale_shape"
OBJECTIVE_SMOOTH_WINDOW = 9
OBJECTIVE_WEIGHT_LEVEL = 0.10
OBJECTIVE_WEIGHT_SHAPE = 0.30
OBJECTIVE_WEIGHT_SLOPE = 0.60

SEARCH_COARSE_D_STEP_NM = 1.0
SEARCH_COARSE_THETA_STEP_DEG = 0.1
SEARCH_TOP_K = 4
SEARCH_MIN_D_SEPARATION_NM = 4.0
SEARCH_MIN_THETA_SEPARATION_DEG = 0.08

REFINE_D_WINDOWS_NM = (8.0, 2.0, 0.5)
REFINE_THETA_WINDOWS_DEG = (0.35, 0.10, 0.025)
REFINE_D_GRID_POINTS = 81
REFINE_THETA_GRID_POINTS = 61
REFINE_COORDINATE_CYCLES = 2


# =========================================================
# 1. 路径配置
# =========================================================
OUTPUT_DIR = Path(r"C:\Users\L2791\thinfilm_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sync_angle_config_aliases() -> None:
    global CSV_FILE_0DEG, CSV_FILE_2DEG
    global FIT_Y_SELECTOR_0DEG, FIT_Y_SELECTOR_2DEG
    global MIX_SOURCE_0DEG_MODE, MIX_SOURCE_2DEG_MODE
    global MIX_SOURCE_CSV_0DEG_S, MIX_SOURCE_CSV_0DEG_P
    global MIX_SOURCE_CSV_2DEG_S, MIX_SOURCE_CSV_2DEG_P

    CSV_FILE_0DEG = CSV_FILE_ANGLE1
    CSV_FILE_2DEG = CSV_FILE_ANGLE2
    FIT_Y_SELECTOR_0DEG = FIT_Y_SELECTOR_ANGLE1
    FIT_Y_SELECTOR_2DEG = FIT_Y_SELECTOR_ANGLE2
    MIX_SOURCE_0DEG_MODE = MIX_SOURCE_ANGLE1_MODE
    MIX_SOURCE_2DEG_MODE = MIX_SOURCE_ANGLE2_MODE
    MIX_SOURCE_CSV_0DEG_S = MIX_SOURCE_CSV_ANGLE1_S
    MIX_SOURCE_CSV_0DEG_P = MIX_SOURCE_CSV_ANGLE1_P
    MIX_SOURCE_CSV_2DEG_S = MIX_SOURCE_CSV_ANGLE2_S
    MIX_SOURCE_CSV_2DEG_P = MIX_SOURCE_CSV_ANGLE2_P
    push_runtime_config()


def format_angle_label(theta_deg: float) -> str:
    rounded = round(float(theta_deg), 6)
    if abs(rounded - round(rounded)) < 1e-6:
        return f"{int(round(rounded))}deg"
    return f"{rounded:g}deg"


def calibrate_thickness_nm(
    d_nm: float,
    use_calibration: bool = USE_THICKNESS_CALIBRATION,
    a: float = CAL_A,
    b: float = CAL_B,
) -> float:
    if not use_calibration:
        return float(d_nm)
    return float(a * d_nm + b)

# ---------- 其它模式默认参数（防止切换 RUN_MODE 时 NameError） ----------
PREVIEW_CSV_FILE = CSV_FILE_2DEG
PREVIEW_Y_SELECTOR: Optional[Union[int, str]] = FIT_Y_SELECTOR_2DEG

EXPORT_CLEAN_INPUT_FILE = CSV_FILE_2DEG
EXPORT_CLEAN_OUTPUT_FILE = OUTPUT_DIR / "clean_export.csv"
EXPORT_Y_SELECTOR: Optional[Union[int, str]] = FIT_Y_SELECTOR_2DEG

FIXED_D_COMPARE_NM = 90.0
FIXED_THETA_COMPARE_DEG = 80.0

THETA2_SCAN_FIXED_D_NM = 90.0
THETA2_SCAN_MIN_DEG = 70.0
THETA2_SCAN_MAX_DEG = 90.0
THETA2_SCAN_STEP_DEG = 0.1
THETA2_SCAN_POL = "p"

BATCH_INPUT_DIR = Path(r"C:\Users\L2791\generated_batch_csv")
BATCH_LABEL_1 = "0deg"
BATCH_LABEL_2 = "80deg_p"
TRUE_THICKNESS_REGEX = r"(\d+(?:\.\d+)?)\s*nm"
TRUE_THICKNESS_FALLBACK_FIRST_NUMBER = True

SINGLE_SAMPLE_TRUE_THICKNESS_NM: Optional[float] = None
SINGLE_SAMPLE_REPORT_ID = "single_case"
SINGLE_SAMPLE_THETA2_HALF_RANGE_DEG = 0.08
SINGLE_SAMPLE_THETA2_STEP_DEG = 0.002
SINGLE_SAMPLE_N1_RELATIVE_HALF_RANGE = 0.03
SINGLE_SAMPLE_N2_RELATIVE_HALF_RANGE = 0.03
SINGLE_SAMPLE_N_SCAN_POINTS = 31
POL_COMPARE_LIST = ("s", "p", "avg", "mix")
POL_COMPARE_REPORT_ID = "single_case_pol_compare"

SCAN_D_MIN_NM = 5.0
SCAN_D_MAX_NM = 200.0
SCAN_D_STEP_NM = 0.2

HEATMAP_D_MIN_NM = 5.0
HEATMAP_D_MAX_NM = 200.0
HEATMAP_D_STEP_NM = 1.0

HEATMAP_THETA2_MIN_DEG = 70.0
HEATMAP_THETA2_MAX_DEG = 90.0
HEATMAP_THETA2_STEP_DEG = 0.25


# =========================================================
# 4. 数据结构
# =========================================================


def _config_export_names() -> List[str]:
    return [
        name for name, value in globals().items()
        if name.isupper() and not name.startswith("_")
    ]


CONFIG_EXPORT_NAMES = _config_export_names()
RUNTIME_MODULE_NAMES = (
    "thinfilm.io",
    "thinfilm.optics",
    "thinfilm.objectives",
    "thinfilm.fitting",
    "thinfilm.diagnostics",
)


def push_runtime_config() -> None:
    import sys

    for module_name in RUNTIME_MODULE_NAMES:
        module = sys.modules.get(module_name)
        if module is None:
            continue
        for name in CONFIG_EXPORT_NAMES:
            setattr(module, name, globals()[name])

