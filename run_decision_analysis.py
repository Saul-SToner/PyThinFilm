"""Export physics-aware scores, uncertainty intervals, and Pareto candidates."""

from __future__ import annotations

import argparse

from thinfilm.decision import build_decision_record, export_decision_analysis, sample_score_uncertainty
from thinfilm.education import simulate_report_chapter2_suite


DEFAULT_CASES = ("single_ar", "double_ar", "high_reflector", "fp_filter")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", default=list(DEFAULT_CASES))
    parser.add_argument("--prefix", default="physics_aware_decision")
    parser.add_argument("--response-sigma", type=float, default=0.002, help="Declared 1σ response uncertainty")
    parser.add_argument("--wavelength-sigma", type=float, default=0.2, help="Declared 1σ wavelength uncertainty in nm")
    parser.add_argument("--samples", type=int, default=300)
    args = parser.parse_args()
    suite = simulate_report_chapter2_suite()
    records = []
    for idx, case_id in enumerate(args.cases):
        if case_id not in suite:
            raise KeyError(f"Unknown case: {case_id}")
        result = suite[case_id]
        score_samples = sample_score_uncertainty(
            case_id=case_id,
            wavelength=result["wavelength_nm"],
            R=result["R"], T=result["T"], A=result["A"],
            design_wavelength=float(result["lambda0_nm"]),
            response_sigma=args.response_sigma,
            wavelength_sigma=args.wavelength_sigma,
            samples=args.samples,
            seed=idx,
        )
        record = build_decision_record(
            case_id=case_id,
            title=str(result.get("title_cn") or case_id),
            wavelength=result["wavelength_nm"],
            R=result["R"], T=result["T"], A=result["A"],
            design_wavelength=float(result["lambda0_nm"]),
            score_samples=score_samples,
        )
        record["uncertainty_assumptions"] = {
            "response_sigma": args.response_sigma,
            "wavelength_sigma_nm": args.wavelength_sigma,
            "samples": args.samples,
        }
        records.append(record)
    files = export_decision_analysis(records, prefix=args.prefix)
    print("物理判据决策分析已导出")
    for key, value in files.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
