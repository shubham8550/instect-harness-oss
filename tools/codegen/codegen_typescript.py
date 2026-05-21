# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Instect, Inc.
"""Zod + inferred-TS emitter — wraps the `json-schema-to-zod` Node CLI.

For each input schema we produce one `.ts` module containing the Zod schema
plus an inferred TypeScript type. The barrel `index.ts` re-exports each
module so consumers can `import { EvalSpec } from '@instect/core/_generated'`.

We require `npx` on PATH; the CLI is invoked as `npx -y json-schema-to-zod`
to fetch on demand without polluting the workspace. The output is then
post-processed to prepend our SPDX + `@generated` header.
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
    """Turn `insect.eval.v1/common.json` → `insect_eval_v1__common`.

    `rel_path` must already be relative to `schemas_root`.
    """
    stripped = rel_path.with_suffix("")
    parts = [p.replace(".", "_").replace("-", "_") for p in stripped.parts]
    return "__".join(parts)


def _emit_empty_barrel(out_dir: Path) -> None:
    (out_dir / "index.ts").write_text(
        GENERATED_HEADER + "// Empty until schemas land.\nexport {};\n"
    )


def _emit_one(schema_path: Path, schemas_root: Path, out_dir: Path) -> str | None:
    try:
        rel = schema_path.relative_to(schemas_root)
    except ValueError:
        rel = Path(schema_path.name)
    mod = _module_name(rel)
    target = out_dir / f"{mod}.ts"

    if shutil.which("npx") is None:
        print(
            "[codegen-typescript] `npx` not on PATH; install Node 22 LTS + pnpm",
            file=sys.stderr,
        )
        return None

    # json-schema-to-zod CLI: write the zod schema to stdout, we redirect.
    cmd = [
        "npx",
        "-y",
        "json-schema-to-zod@2",
        "--input",
        str(schema_path),
        "--name",
        mod,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("[codegen-typescript] could not exec `npx`", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as exc:
        print(
            f"[codegen-typescript] json-schema-to-zod failed for {schema_path}:\n{exc.stderr}",
            file=sys.stderr,
        )
        return None

    body = result.stdout
    inferred = (
        f"\nexport type {mod}_T = import('zod').z.infer<typeof {mod}>;\n"
        if "export const " + mod in body or "const " + mod in body
        else ""
    )
    target.write_text(GENERATED_HEADER + body + inferred)
    return mod


def generate(schemas: list[Path], schemas_root: Path, out_dir: Path) -> None:
    for child in out_dir.iterdir() if out_dir.exists() else []:
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    if not schemas:
        _emit_empty_barrel(out_dir)
        return

    modules: list[str] = []
    for s in schemas:
        m = _emit_one(s, schemas_root, out_dir)
        if m is not None:
            modules.append(m)

    barrel = [GENERATED_HEADER]
    if not modules:
        barrel.append("// Empty until schemas land.\nexport {};\n")
    else:
        for m in sorted(modules):
            barrel.append(f"export * from './{m}.js';\n")
    (out_dir / "index.ts").write_text("".join(barrel))
