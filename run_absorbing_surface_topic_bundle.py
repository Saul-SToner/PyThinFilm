from __future__ import annotations

from pathlib import Path

from thinfilm import export_absorbing_surface_topic


def main() -> None:
    data_dir = Path(r"C:\Users\L2791\OneDrive\Desktop\deg.p")
    roughness_files = {
        0.25: str(data_dir / "2D periodic quasi-random rough absorbing surface(0.25).csv"),
        0.5: str(data_dir / "2D periodic quasi-random rough absorbing surface(0.5).csv"),
        0.75: str(data_dir / "2D periodic quasi-random rough absorbing surface(0.75).csv"),
        1.0: str(data_dir / "2D periodic quasi-random rough absorbing surface.csv"),
        1.1: str(data_dir / "2D periodic quasi-random rough absorbing surface(1.1).csv"),
        1.15: str(data_dir / "2D periodic quasi-random rough absorbing surface(1.15).csv"),
    }
    baseline_csv = str(data_dir / "2D periodic quasi-random rough absorbing surface(basic).csv")
    best_rough_csv = str(data_dir / "2D periodic quasi-random rough absorbing surface(1.15).csv")

    result = export_absorbing_surface_topic(
        baseline_csv=baseline_csv,
        best_rough_csv=best_rough_csv,
        best_rough_label="粗糙表面 1.15x",
        roughness_files=roughness_files,
        prefix="rough_absorbing_surface_topic_v1",
        lambda0_nm=550.0,
    )
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
