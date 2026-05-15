from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from pathlib import Path

from thinfilm import export_tamm_phase_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出 Tamm 吸收器 d_W-相位联合扫描结果，用于第 2 阶段反射相位与拓扑分类。"
    )
    parser.add_argument(
        "--csv",
        default=r"C:\Users\L2791\OneDrive\Desktop\deg.p\tamm_spectrum_dW_scan(4).csv",
        help="包含 d_W 联合扫描与 S11 相位列的 COMSOL CSV 路径",
    )
    parser.add_argument(
        "--prefix",
        default="tamm_dw_phase_v1",
        help="输出文件前缀",
    )
    parser.add_argument(
        "--lambda-min-um",
        type=float,
        default=None,
        help="可选：波长窗口下限（μm）",
    )
    parser.add_argument(
        "--lambda-max-um",
        type=float,
        default=None,
        help="可选：波长窗口上限（μm）",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    window = None
    if args.lambda_min_um is not None and args.lambda_max_um is not None:
        window = (float(args.lambda_min_um), float(args.lambda_max_um))

    result = export_tamm_phase_bundle(
        reference_csv=Path(args.csv),
        prefix=str(args.prefix),
        lambda_window_um=window,
    )
    print("Tamm 第2阶段相位分析总包已导出")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
