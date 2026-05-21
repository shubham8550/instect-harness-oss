#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Instect, Inc.
"""Cross-language codegen orchestrator for the `insect.eval.v1` JSON Schema family.

Given a `--schemas-dir`, this script emits Pydantic v2 models (Python), Zod
schemas + inferred TS types (TypeScript), and Rust structs (via `typify`) into
the three configured output directories.

In `--mode=generate` outputs are written in place. In `--mode=check`, outputs
are written to a tempdir and diffed against the committed outputs; any drift
returns a non-zero exit code with a helpful regenerate hint.

The pipeline must be reproducible: same inputs → identical outputs, byte-for-
byte where the toolchain permits. We sort schema inputs lexicographically and
strip toolchain-specific volatile lines (timestamps, absolute paths) in each
language emitter.

When `--schemas-dir` is empty (or contains no `.json` files), the script
produces a valid-but-empty set of outputs (empty barrel files) — it does not
crash. That lets the pipeline land before the W2-C schemas land.
"""

from __future__ import annotations

import argparse
import difflib
import filecmp
import os
import shutil
import sys
import tempfile
from pathlib import Path

import codegen_python
import codegen_rust
import codegen_typescript

REGEN_HINT = (
    "drift detected between committed `_generated/` outputs and a fresh codegen "
    "run. Run `just codegen` (or `uv run python tools/codegen/codegen.py "
    "--mode=generate ...`) and commit the updated files."
)


def _collect_schemas(schemas_dir: Path) -> list[Path]:
    """Return all `*.json` schema files under `schemas_dir`, sorted for determinism."""
    if not schemas_dir.exists():
        return []
    return sorted(p for p in schemas_dir.rglob("*.json") if p.is_file())


def _run_generators(
    schemas: list[Path],
    schemas_root: Path,
    out_py: Path,
    out_ts: Path,
    out_rust: Path,
) -> None:
    """Invoke all three language emitters."""
    out_py.mkdir(parents=True, exist_ok=True)
    out_ts.mkdir(parents=True, exist_ok=True)
    out_rust.mkdir(parents=True, exist_ok=True)

    codegen_python.generate(schemas, schemas_root, out_py)
    codegen_typescript.generate(schemas, schemas_root, out_ts)
    codegen_rust.generate(schemas, schemas_root, out_rust)


def _diff_dirs(committed: Path, generated: Path) -> list[str]:
    """Return a list of diff descriptions; empty if the dirs match byte-for-byte."""
    diffs: list[str] = []

    def _walk(rel_root: Path) -> None:
        com_root = committed / rel_root
        gen_root = generated / rel_root
        com_entries = {p.name for p in com_root.iterdir()} if com_root.exists() else set()
        gen_entries = {p.name for p in gen_root.iterdir()} if gen_root.exists() else set()

        for name in sorted(com_entries | gen_entries):
            com_p = com_root / name
            gen_p = gen_root / name
            rel = rel_root / name
            if name in com_entries and name not in gen_entries:
                diffs.append(f"only in committed: {rel}")
                continue
            if name in gen_entries and name not in com_entries:
                diffs.append(f"only in generated: {rel}")
                continue
            if com_p.is_dir() and gen_p.is_dir():
                _walk(rel)
                continue
            if com_p.is_file() and gen_p.is_file():
                if filecmp.cmp(com_p, gen_p, shallow=False):
                    continue
                try:
                    com_text = com_p.read_text().splitlines(keepends=True)
                    gen_text = gen_p.read_text().splitlines(keepends=True)
                    udiff = "".join(
                        difflib.unified_diff(
                            com_text,
                            gen_text,
                            fromfile=f"committed/{rel}",
                            tofile=f"generated/{rel}",
                            n=2,
                        )
                    )
                    diffs.append(f"differs: {rel}\n{udiff}")
                except UnicodeDecodeError:
                    diffs.append(f"differs (binary): {rel}")
                continue
            diffs.append(f"type-mismatch: {rel}")

    _walk(Path("."))
    return diffs


def _check_mode(
    schemas: list[Path],
    schemas_root: Path,
    out_py: Path,
    out_ts: Path,
    out_rust: Path,
) -> int:
    with tempfile.TemporaryDirectory(prefix="insect-codegen-check-") as td:
        tmp = Path(td)
        tmp_py = tmp / "py"
        tmp_ts = tmp / "ts"
        tmp_rust = tmp / "rust"
        _run_generators(schemas, schemas_root, tmp_py, tmp_ts, tmp_rust)

        any_diffs = False
        for label, committed, generated in (
            ("python", out_py, tmp_py),
            ("typescript", out_ts, tmp_ts),
            ("rust", out_rust, tmp_rust),
        ):
            committed.mkdir(parents=True, exist_ok=True)
            diffs = _diff_dirs(committed, generated)
            if diffs:
                any_diffs = True
                print(f"[drift-check] {label}: {len(diffs)} difference(s)", file=sys.stderr)
                for d in diffs:
                    print(f"  - {d}", file=sys.stderr)

        if any_diffs:
            print(f"\n[drift-check] {REGEN_HINT}", file=sys.stderr)
            return 1
        print("[drift-check] ok: committed outputs match a fresh codegen run.")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schemas-dir", type=Path, required=True, help="root of JSON Schema sources")
    ap.add_argument("--out-py", type=Path, required=True, help="Pydantic output dir")
    ap.add_argument("--out-ts", type=Path, required=True, help="Zod/TS output dir")
    ap.add_argument("--out-rust", type=Path, required=True, help="Rust output dir")
    ap.add_argument(
        "--mode",
        choices=("generate", "check"),
        default="generate",
        help="`generate` writes outputs in place; `check` writes to a tempdir and diffs",
    )
    args = ap.parse_args(argv)

    schemas_dir: Path = args.schemas_dir.resolve()
    out_py: Path = args.out_py.resolve()
    out_ts: Path = args.out_ts.resolve()
    out_rust: Path = args.out_rust.resolve()

    schemas = _collect_schemas(schemas_dir)
    if not schemas:
        print(
            f"[codegen] no `*.json` schemas found under {schemas_dir}; "
            "emitting empty-but-valid outputs.",
            file=sys.stderr,
        )

    if args.mode == "generate":
        _run_generators(schemas, schemas_dir, out_py, out_ts, out_rust)
        print(f"[codegen] wrote outputs for {len(schemas)} schema file(s).")
        return 0
    return _check_mode(schemas, schemas_dir, out_py, out_ts, out_rust)


if __name__ == "__main__":
    # Make sibling modules importable when invoked as a script via uv/python.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
