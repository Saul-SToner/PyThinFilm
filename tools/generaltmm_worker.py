"""One-request GeneralTmm worker for the bundled, non-frozen CPython runtime."""

import json
import sys

from solver import generaltmm_adapter


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"__complex__"}:
            return complex(*value["__complex__"])
        return {key: decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode(item) for item in value]
    return value


def main() -> None:
    try:
        request = json.load(sys.stdin)
        allowed = ("solve_interface", "sweep_interface", "sweep_multilayer", "multilayer_field_comparison")
        operation = request["operation"]
        if operation not in allowed:
            raise ValueError(f"Unsupported GeneralTmm operation: {operation}")
        result = getattr(generaltmm_adapter, operation)(**decode(request["arguments"]))
        response = {"ok": True, "result": generaltmm_adapter._encode(result)}
    except Exception as exc:
        response = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
