# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Instect, Inc.
"""Rust emitter — wraps the `typify` CLI.

Toolchain choice (vs. alternatives):

  * `typify` (Oxide Computer): generates idiomatic `#[derive(Serialize,
    Deserialize, JsonSchema)]` structs and enums directly from JSON Schema
    Draft 2020-12. Tracks discriminated unions correctly. **Our choice.**
  * `schemars`: generates JSON Schema *from* Rust structs — opposite
    direction; only useful for round-trip drift-check, not first-pass codegen.
  * `quicktype`: TS-leaning, weaker on JSON Schema 2020-12 idioms, emits
    `#[allow(...)]` heavy code that fights `clippy -D warnings`. Skipped.

We invoke `typify` as a binary. The justfile recipe installs it via
`cargo install typify-cli` on first use.

If `typify` isn't on PATH we fail soft (emit empty mod.rs + warn) so the
pipeline still runs during early bootstrap. The drift-check in CI will
guarantee the toolchain is available there.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

GENERATED_HEADER = (
    "// SPDX-License-Identifier: Apache-2.0\n"
    "// SPDX-FileCopyrightText: 2026 Instect, Inc.\n"
    "// @generated — DO NOT EDIT. Regenerate via `just codegen`.\n"
)


def _module_name(rel_path: Path) -> str:
    """`rel_path` must already be relative to `schemas_root`."""
    stripped = rel_path.with_suffix("")
    parts = [p.replace(".", "_").replace("-", "_") for p in stripped.parts]
    return "__".join(parts)


def _emit_empty_mod(out_dir: Path) -> None:
    (out_dir / "mod.rs").write_text(
        GENERATED_HEADER + "//! Empty until schemas land.\n"
    )


def _emit_one(schema_path: Path, schemas_root: Path, out_dir: Path) -> str | None:
    try:
        rel = schema_path.relative_to(schemas_root)
    except ValueError:
        rel = Path(schema_path.name)
    mod = _module_name(rel)
    target = out_dir / f"{mod}.rs"

    if shutil.which("typify") is None:
        print(
            "[codegen-rust] `typify` not on PATH; install with "
            "`cargo install typify-cli` (skipping for now)",
            file=sys.stderr,
        )
        return None

    cmd = ["typify", "--output", str(target), str(schema_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"[codegen-rust] typify failed for {schema_path}:\n{exc.stderr}",
            file=sys.stderr,
        )
        return None

    if target.exists():
        body = target.read_text()
        target.write_text(GENERATED_HEADER + body)
    return mod


def generate(schemas: list[Path], schemas_root: Path, out_dir: Path) -> None:
    for child in out_dir.iterdir() if out_dir.exists() else []:
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    if not schemas:
        _emit_empty_mod(out_dir)
        return

    modules: list[str] = []
    for s in schemas:
        m = _emit_one(s, schemas_root, out_dir)
        if m is not None:
            modules.append(m)

    lines = [GENERATED_HEADER, "//! Generated Rust types from `insect.eval.v1` JSON Schema.\n\n"]
    if not modules:
        lines.append("// Empty until schemas land or `typify` is installed.\n")
    else:
        for m in sorted(modules):
            lines.append(f"pub mod {m};\n")
    (out_dir / "mod.rs").write_text("".join(lines))
