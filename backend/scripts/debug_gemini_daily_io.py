"""
Smoke test: PROD snapshot + sector-flow -> prompt kiểu legacy (build_gemini_prompt_for_smoke) -> Gemini JSON.

Lưu ý: pipeline production `daily-balanced-run` **không** gọi Gemini; script này chỉ để kiểm I/O model.

Run from `backend/` with PYTHONPATH including this directory, with secrets in env:

  # Production vars (e.g. injected by `railway run` from linked backend service)
  set GOOGLE_GEMINI_API_KEY=...
  set PYTHONPATH=.
  python scripts/debug_gemini_daily_io.py

Or: railway run -- python scripts/debug_gemini_daily_io.py

Optional env (smoke call only, not production automation):
- GEMINI_SMOKE_MAX_OUTPUT_TOKENS / GEMINI_SMOKE_REPAIR_MAX_OUTPUT_TOKENS (default 131072) — output đủ lớn để khớp schema plan; nếu vẫn MAX_TOKENS thì tăng thêm.
- GEMINI_SMOKE_USE_PRODUCTION_CAP=1 — gọi `_run_gemini_production_cap` (1800 token) như cap cũ trước khi bỏ Gemini; gần như chắc cắt JSON → exit 4 nếu bật kiểm schema.
- GEMINI_SMOKE_SKIP_SCHEMA_CHECK=1 — không kiểm tra đủ key plan (chỉ dùng khi debug); mặc định bắt buộc đủ schema mới exit 0.

Exit codes (đừng báo “chạy xong plan” nếu exit != 0):
  0 = PROD fetch + Gemini + JSON đủ schema theo mục (4) plan (title, reference_date, selected_signals, sector_flow_analysis, near_miss_signals, analysis_notes).
  1 = Thiếu GOOGLE_GEMINI_API_KEY.
  2 = Thiếu file prompt markdown.
  3 = Lỗi mạng/API Gemini (exception).
  4 = Gemini trả JSON nhưng thiếu/sai schema hoặc cắt output (MAX_TOKENS).
  5 = Lỗi tải PROD snapshot / sector-flow.

Artifacts trong backend/gemini_smoke/ (gitignored):
  - gemini_input_prompt.txt — đúng input gửi model (markdown + 2 khối JSON compact).
  - gemini_output.json — bản đầy đủ + _smoke_meta + _plan_validation.
  - gemini_report.txt — tóm tắt STATUS + meta bảng plan + đường dẫn file (mở file này trước).
  - gemini_output_README.txt — một dòng trạng thái nhanh.

Fallback: GEMINI_SMOKE_OUT_DIR = đường dẫn tuyệt đối khác.

Do not commit smoke artifacts; they may contain market/news text.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import httpx

# Ensure `backend/` is on path when run as `python scripts/debug_gemini_daily_io.py`
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from config import settings  # noqa: E402
from services.daily_automation_service import _http_json  # noqa: E402
from services.gemini_smoke_prompt import build_gemini_prompt_for_smoke  # noqa: E402


PROD_BASE = os.environ.get(
    "PROD_BASE_URL",
    "https://vnindex-signal-production.up.railway.app",
).rstrip("/")


def _smoke_out_dir() -> Path:
    raw = (os.environ.get("GEMINI_SMOKE_OUT_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    d = (_BACKEND_ROOT / "gemini_smoke").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _fetch_json(client: httpx.AsyncClient, url: str) -> dict:
    r = await client.get(url)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object from {url}")
    return data


def _mask_key(raw: str | None) -> str:
    if not raw or not str(raw).strip():
        return "(missing)"
    return f"(set, length={len(str(raw).strip())})"


def _ensure_utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


async def _run_gemini_production_cap(prompt: str) -> dict[str, Any]:
    """Gọi Gemini với maxOutputTokens=1800 như bản production cũ (script smoke / so sánh hành vi)."""
    if not settings.google_gemini_api_key:
        raise RuntimeError("Missing GOOGLE_GEMINI_API_KEY")
    model = settings.gemini_model.strip() or "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.google_gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.05,
            "responseMimeType": "application/json",
            "maxOutputTokens": 1800,
        },
    }
    timeout = max(30, int(settings.automation_http_timeout_seconds))
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await _http_json(client, "POST", url, json=payload)

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini response has no candidates")
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise RuntimeError("Gemini response has invalid content parts")
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    out = "\n".join(chunks).strip()
    if not out:
        raise RuntimeError("Gemini returned empty text")
    try:
        obj = json.loads(out)
    except Exception:
        repair_payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Convert the following malformed JSON-like text into VALID JSON object only. "
                                "Do not add markdown.\n\n"
                                f"{out}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 1800,
            },
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            repaired_data = await _http_json(client, "POST", url, json=repair_payload)
        repaired_candidates = repaired_data.get("candidates")
        if not isinstance(repaired_candidates, list) or not repaired_candidates:
            raise RuntimeError("Gemini JSON repair failed: no candidates")
        repaired_content = repaired_candidates[0].get("content") if isinstance(repaired_candidates[0], dict) else None
        repaired_parts = repaired_content.get("parts") if isinstance(repaired_content, dict) else None
        repaired_text = ""
        if isinstance(repaired_parts, list):
            repaired_text = "\n".join(
                [p.get("text") for p in repaired_parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
            ).strip()
        try:
            obj = json.loads(repaired_text)
        except Exception as e:
            raise RuntimeError(f"Gemini JSON parse failed: {e}") from e
    if not isinstance(obj, dict):
        raise RuntimeError("Gemini response is not a JSON object")
    return obj


async def _run_gemini_smoke_high_budget(prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Giống contract JSON `_run_gemini_production_cap` nhưng maxOutputTokens lớn (prompt dài dễ vượt 1800)."""
    if not settings.google_gemini_api_key:
        raise RuntimeError("Missing GOOGLE_GEMINI_API_KEY")
    model = settings.gemini_model.strip() or "gemini-2.0-flash"
    max_out = int(os.environ.get("GEMINI_SMOKE_MAX_OUTPUT_TOKENS", "131072"))
    repair_max = int(os.environ.get("GEMINI_SMOKE_REPAIR_MAX_OUTPUT_TOKENS", str(max_out)))
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.google_gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.05,
            "responseMimeType": "application/json",
            "maxOutputTokens": max_out,
        },
    }
    timeout = max(60, int(settings.automation_http_timeout_seconds))
    meta: dict[str, Any] = {"maxOutputTokens": max_out, "finishReason": None, "used_repair": False}
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await _http_json(client, "POST", url, json=payload)
    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
        meta["finishReason"] = candidates[0].get("finishReason")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini response has no candidates")
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise RuntimeError("Gemini response has invalid content parts")
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    out = "\n".join(chunks).strip()
    if not out:
        raise RuntimeError("Gemini returned empty text")
    try:
        obj = json.loads(out)
    except Exception:
        meta["used_repair"] = True
        repair_payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Convert the following malformed JSON-like text into VALID JSON object only. "
                                "Do not add markdown.\n\n"
                                f"{out}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "maxOutputTokens": repair_max,
            },
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            repaired_data = await _http_json(client, "POST", url, json=repair_payload)
        repaired_candidates = repaired_data.get("candidates")
        if not isinstance(repaired_candidates, list) or not repaired_candidates:
            raise RuntimeError("Gemini JSON repair failed: no candidates")
        repaired_content = repaired_candidates[0].get("content") if isinstance(repaired_candidates[0], dict) else None
        repaired_parts = repaired_content.get("parts") if isinstance(repaired_content, dict) else None
        repaired_text = ""
        if isinstance(repaired_parts, list):
            repaired_text = "\n".join(
                [p.get("text") for p in repaired_parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
            ).strip()
        try:
            obj = json.loads(repaired_text)
        except Exception as e:
            raise RuntimeError(f"Gemini JSON parse failed: {e}") from e
    if not isinstance(obj, dict):
        raise RuntimeError("Gemini response is not a JSON object")
    return obj, meta


def _snapshot_symbol_count(snapshot_data: dict[str, Any]) -> int:
    payload = snapshot_data.get("payload") if isinstance(snapshot_data.get("payload"), dict) else snapshot_data
    if not isinstance(payload, dict):
        return 0
    syms = payload.get("symbols")
    return len(syms) if isinstance(syms, list) else 0


def _validate_plan_deliverable(resp: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """The plan table requires these top-level keys and basic types."""
    errs: list[str] = []
    if not isinstance(resp, dict):
        return False, ["gemini_response is missing or not a JSON object"]
    required = (
        "title",
        "reference_date",
        "selected_signals",
        "sector_flow_analysis",
        "near_miss_signals",
        "analysis_notes",
    )
    for k in required:
        if k not in resp:
            errs.append(f"missing required key: {k}")
    if errs:
        return False, errs
    if not isinstance(resp.get("title"), str) or not str(resp["title"]).strip():
        errs.append("title must be a non-empty string")
    rd = resp.get("reference_date")
    if not isinstance(rd, str) or len(rd.strip()) < 10:
        errs.append("reference_date must be a non-empty string (e.g. YYYY-MM-DD)")
    for lk in ("selected_signals", "sector_flow_analysis", "near_miss_signals"):
        if not isinstance(resp.get(lk), list):
            errs.append(f"{lk} must be a JSON array")
    an = resp.get("analysis_notes")
    if an is not None and not isinstance(an, str):
        errs.append("analysis_notes must be string or null")
    return len(errs) == 0, errs


def _write_output_file(
    out_dir: Path,
    *,
    smoke_meta: dict[str, Any],
    gemini_response: dict[str, Any] | None,
    error: str | None = None,
    plan_validation: dict[str, Any] | None = None,
) -> Path:
    out_json = out_dir / "gemini_output.json"
    body: dict[str, Any] = {"_smoke_meta": smoke_meta, "gemini_response": gemini_response}
    if error:
        body["_error"] = error
    if plan_validation is not None:
        body["_plan_validation"] = plan_validation
    out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_json


def _write_status_files(
    out_dir: Path,
    *,
    status: str,
    detail_lines: list[str],
    smoke_meta: dict[str, Any],
    error: str | None,
) -> None:
    # UTF-8 BOM: một số editor Windows mở đúng tiếng Việt hơn
    bom = "\ufeff"
    readme = out_dir / "gemini_output_README.txt"
    readme.write_text(bom + f"STATUS={status}\n" + "\n".join(detail_lines) + "\n", encoding="utf-8")
    report = out_dir / "gemini_report.txt"
    report.write_text(
        bom
        + "\n".join(
            [
                "Gemini I/O smoke — báo cáo (đối chiếu plan)",
                f"STATUS: {status}",
                "",
                *detail_lines,
                "",
                f"_smoke_meta: {json.dumps(smoke_meta, ensure_ascii=False)}",
                "",
                "Nếu STATUS không phải SUCCESS thì chưa đạt deliverable plan — không coi là 'chạy xong' smoke test.",
                f"Lỗi: {error}" if error else "",
            ]
        ).strip()
        + "\n",
        encoding="utf-8",
    )


async def main() -> int:
    _ensure_utf8_stdout()
    out_dir = _smoke_out_dir()
    snap_url = f"{PROD_BASE}/api/v1/balanced/snapshot"
    sec_url = f"{PROD_BASE}/api/v1/balanced/sector-flow-5d"

    prompt_path = _BACKEND_ROOT / "prompt-signal-cash-flow.md"
    if not prompt_path.is_file():
        print(f"Missing prompt file: {prompt_path}", file=sys.stderr)
        return 2

    base_prompt = prompt_path.read_text(encoding="utf-8")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            snapshot_data = await _fetch_json(client, snap_url)
            sector_data = await _fetch_json(client, sec_url)
    except Exception as e:
        tb = traceback.format_exc()
        err = f"PROD fetch failed: {e}\n{tb}"
        sm: dict[str, Any] = {"stage": "prod_fetch", "exception_type": type(e).__name__}
        pv = {"ok": False, "schema_errors": ["prod_fetch_failed"], "detail": str(e)}
        out_json = _write_output_file(out_dir, smoke_meta=sm, gemini_response=None, error=err, plan_validation=pv)
        _write_status_files(
            out_dir,
            status="PROD_FETCH_FAILED",
            detail_lines=[
                f"Exit code: 5",
                f"Input (prompt not built): —",
                f"Output JSON: {out_json}",
                f"Report: {out_dir / 'gemini_report.txt'}",
            ],
            smoke_meta=sm,
            error=err,
        )
        print(f"Output file (open in editor): {out_json}")
        print(f"Report: {out_dir / 'gemini_report.txt'}")
        print(err, file=sys.stderr)
        return 5

    prompt = build_gemini_prompt_for_smoke(base_prompt, snapshot_data, sector_data)
    sym_count = _snapshot_symbol_count(snapshot_data)
    out_prompt = out_dir / "gemini_input_prompt.txt"
    out_prompt.write_text(prompt, encoding="utf-8")

    print("=== Meta (plan deliverable — Input) ===")
    print(f"PROD_BASE_URL: {PROD_BASE}")
    print(f"snapshot found: {snapshot_data.get('found')}")
    print(f"sector found: {sector_data.get('found')}")
    print(f"prompt_chars: {len(prompt)}")
    print(f"snapshot_symbol_count: {sym_count}")
    print(f"Input file (full text Gemini receives): {out_prompt}")
    print(f"Output directory: {out_dir}")
    print(f"GOOGLE_GEMINI_API_KEY: {_mask_key(settings.google_gemini_api_key)}")
    print(f"GEMINI_MODEL: {settings.gemini_model!r}")
    print()

    if not settings.google_gemini_api_key:
        err = "Missing GOOGLE_GEMINI_API_KEY — use `railway run` from linked backend service or export the key."
        sm = {"stage": "preflight", "key_present": False, "model": settings.gemini_model, "prompt_chars": len(prompt)}
        pv = {"ok": False, "schema_errors": ["cannot_call_gemini_without_key"], "skipped_gemini": True}
        out_json = _write_output_file(out_dir, smoke_meta=sm, gemini_response=None, error=err, plan_validation=pv)
        _write_status_files(
            out_dir,
            status="PREFLIGHT_FAILED",
            detail_lines=[
                "Exit code: 1",
                f"Input: {out_prompt} (written; full prompt per plan)",
                f"Output JSON: {out_json} (gemini_response null)",
                f"Report: {out_dir / 'gemini_report.txt'}",
                "Chưa gọi Gemini — chưa đạt deliverable Output trong plan.",
            ],
            smoke_meta=sm,
            error=err,
        )
        print(f"Output file: {out_json}")
        print(f"Report: {out_dir / 'gemini_report.txt'}")
        print(err, file=sys.stderr)
        return 1

    max_out = int(os.environ.get("GEMINI_SMOKE_MAX_OUTPUT_TOKENS", "131072"))
    use_prod_cap = os.environ.get("GEMINI_SMOKE_USE_PRODUCTION_CAP", "").lower() in ("1", "true", "yes")
    skip_schema = os.environ.get("GEMINI_SMOKE_SKIP_SCHEMA_CHECK", "").lower() in ("1", "true", "yes")
    print(
        "=== Calling Gemini (plan — Output) ===",
        f"production _run_gemini_production_cap (1800 tokens)" if use_prod_cap else f"smoke high budget (maxOutputTokens={max_out})",
    )
    if skip_schema:
        print("WARNING: GEMINI_SMOKE_SKIP_SCHEMA_CHECK=1 — exit 0 không chứng minh đủ deliverable plan.", file=sys.stderr)

    try:
        if use_prod_cap:
            obj = await _run_gemini_production_cap(prompt)
            smoke_meta = {
                "mode": "production_cap_1800",
                "model": settings.gemini_model,
                "prompt_chars": len(prompt),
                "snapshot_symbols": sym_count,
            }
        else:
            obj, gmeta = await _run_gemini_smoke_high_budget(prompt)
            smoke_meta = {
                **gmeta,
                "model": settings.gemini_model,
                "prompt_chars": len(prompt),
                "snapshot_symbols": sym_count,
            }
    except Exception as e:
        tb = traceback.format_exc()
        err = f"{e}\n\n{tb}"
        sm = {
            "stage": "gemini_call",
            "exception_type": type(e).__name__,
            "model": settings.gemini_model,
            "prompt_chars": len(prompt),
        }
        pv = {"ok": False, "schema_errors": ["gemini_exception"], "detail": str(e)}
        out_json = _write_output_file(out_dir, smoke_meta=sm, gemini_response=None, error=err, plan_validation=pv)
        _write_status_files(
            out_dir,
            status="GEMINI_EXCEPTION",
            detail_lines=[
                "Exit code: 3",
                f"Input: {out_prompt}",
                f"Output JSON: {out_json}",
                f"Report: {out_dir / 'gemini_report.txt'}",
            ],
            smoke_meta=sm,
            error=err,
        )
        print(f"Output file: {out_json}")
        print(f"Report: {out_dir / 'gemini_report.txt'}")
        print(f"Gemini call failed: {e}", file=sys.stderr)
        return 3

    n_sig = len(obj["selected_signals"]) if isinstance(obj.get("selected_signals"), list) else None
    if skip_schema:
        ok, schema_errs = True, []
    else:
        ok, schema_errs = _validate_plan_deliverable(obj)
    pv: dict[str, Any] = {
        "ok": ok,
        "schema_errors": schema_errs,
        "selected_signals_count": n_sig,
        "finishReason": smoke_meta.get("finishReason"),
        "used_repair": smoke_meta.get("used_repair"),
        "schema_check_skipped": skip_schema,
    }
    if not ok and smoke_meta.get("finishReason") == "MAX_TOKENS":
        pv["hint"] = "Output bị cắt (MAX_TOKENS). Tăng GEMINI_SMOKE_MAX_OUTPUT_TOKENS hoặc rút prompt/schema."

    out_json = _write_output_file(
        out_dir,
        smoke_meta=smoke_meta,
        gemini_response=obj,
        error=None,
        plan_validation=pv,
    )

    if ok and not skip_schema:
        status = "SUCCESS"
        exit_code = 0
    elif ok and skip_schema:
        status = "SUCCESS_SCHEMA_CHECK_SKIPPED"
        exit_code = 0
    else:
        status = "SCHEMA_INCOMPLETE"
        exit_code = 4

    detail_lines = [
        f"Exit code: {exit_code}",
        f"Input: {out_prompt}",
        f"Output JSON: {out_json}",
        f"Report: {out_dir / 'gemini_report.txt'}",
        f"Model: {settings.gemini_model}",
        f"reference_date (raw): {obj.get('reference_date')!r}",
        f"selected_signals count: {n_sig}",
        f"used_repair: {smoke_meta.get('used_repair')}",
        f"finishReason: {smoke_meta.get('finishReason')!r}",
        f"schema_ok: {ok}",
        f"schema_errors: {schema_errs}",
    ]
    _write_status_files(out_dir, status=status, detail_lines=detail_lines, smoke_meta=smoke_meta, error=None)

    print(f"STATUS: {status} (exit {exit_code})")
    print(f"Output JSON: {out_json}")
    print(f"Report (đọc file này trước): {out_dir / 'gemini_report.txt'}")
    print("=== Gemini response (stdout preview) ===")
    try:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print("(skipped stdout; open gemini_output.json)")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
