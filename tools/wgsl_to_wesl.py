#!/usr/bin/env python3
"""Translates the naga_oil dialect of WGSL (Bevy 0.19) to WESL (Bevy 0.20).

    python3 tools/wgsl_to_wesl.py --crate client --src client/src [--delete] [files...]

With no files, every `.wgsl` under `--src` is translated to a `.wesl` next to it. It does the
mechanical parts and reports, as WARN lines, what it cannot translate safely:

  #define_import_path X     dropped: a module is named by the path of its file (`client::a::b`)
  #import a::{b, c::d}      `import a::b;` `import a::c::d;`, hoisted to the top, with the
                            modules of Bevy renamed (RENAMES) and ours by their file path
  #{NAME}                   `constants::NAME`
  #ifdef / #ifndef / #else  `@if(X)` on each declaration, member or parameter of the region; in
                            a function body, `@if(X) { ... } @else { ... }` (WARN when the block
                            declares a variable, as the braces end its scope)
  #if / #elif / #define     WARN, left as they are

RENAMES marks the paths seen in Bevy 0.20 itself as verified; the others are the same rule
(`bevy_pbr::render::<file>`) applied by guess: the compile test of the shaders settles them.
"""
import argparse
import pathlib
import re
import sys

# Bevy's moved modules: the old path -> the path of its file in 0.20.
RENAMES = {
    # seen in the migration guide, the examples and shaders ported by others
    "bevy_pbr::mesh_view_bindings": "bevy_pbr::render::mesh_view_bindings",
    "bevy_pbr::mesh_functions": "bevy_pbr::render::mesh_functions",
    "bevy_pbr::view_transformations": "bevy_pbr::render::view_transformations",
    "bevy_pbr::forward_io": "bevy_pbr::render::forward_io",
    "bevy_pbr::pbr_functions": "bevy_pbr::render::pbr_functions",
    "bevy_pbr::pbr_types": "bevy_pbr::render::pbr_types",
    "bevy_pbr::pbr_bindings": "bevy_pbr::render::pbr_bindings",
    "bevy_pbr::prepass_io": "bevy_pbr::prepass::io",
    "bevy_pbr::prepass_utils": "bevy_pbr::prepass::utils",
    # the same rule, not seen: check them
    "bevy_pbr::pbr_fragment": "bevy_pbr::render::pbr_fragment",
    "bevy_pbr::pbr_prepass_functions": "bevy_pbr::render::pbr_prepass_functions",
    "bevy_pbr::mesh_view_types": "bevy_pbr::render::mesh_view_types",
    "bevy_pbr::mesh_bindings": "bevy_pbr::render::mesh_bindings",
    "bevy_pbr::mesh_types": "bevy_pbr::render::mesh_types",
    "bevy_pbr::shadows": "bevy_pbr::render::shadows",
    "bevy_pbr::prepass_bindings": "bevy_pbr::prepass::bindings",
}
UNVERIFIED = {
    "bevy_pbr::pbr_fragment",
    "bevy_pbr::pbr_prepass_functions",
    "bevy_pbr::mesh_view_types",
    "bevy_pbr::mesh_bindings",
    "bevy_pbr::mesh_types",
    "bevy_pbr::shadows",
    "bevy_pbr::prepass_bindings",
}

STATEMENT = ("fn", "block")

# Imported names that 0.20 declares only conditionally, or changed.
IMPORT_HAZARDS = {
    "view_transmission_texture": "bevy_pbr 0.20 declares it only with VIEW_TRANSMISSION_TEXTURE: "
    "the camera needs `ScreenSpaceTransmission` (no longer a required component), and the import "
    "needs `@if(VIEW_TRANSMISSION_TEXTURE)`",
    "view_transmission_sampler": "as view_transmission_texture",
}
# Code that 0.20 changed.
CODE_HAZARDS = [
    (r"\balpha_discard\(", "0.20: `alpha_discard` and the prepass discard take flags, cutoff "
     "and colour: check the signature in bevy_pbr::render::pbr_functions"),
    (r"\bpbr_bindings::material\b", "0.20: check how the standard material is bound "
     "(`pbr_bindings`, bindless)"),
]


class Report:
    def __init__(self):
        self.warnings = []
        self.unverified = set()

    def warn(self, path, line, message):
        self.warnings.append(f"WARN {path}:{line}: {message}")


def strip_comment(line):
    return line.split("//", 1)[0]


def rename(path, table, report):
    for old in sorted(table, key=len, reverse=True):
        if path == old or path.startswith(old + "::"):
            if old in UNVERIFIED:
                report.unverified.add(old)
            return table[old] + path[len(old):]
    return path


def parse_group(tokens, pos, prefix):
    """The (segments, alias) of the items of `a::{b, c::{d}}` from `pos`, to the closing brace."""
    results = []
    while pos < len(tokens):
        token = tokens[pos]
        if token == "}":
            return results, pos + 1
        if token == ",":
            pos += 1
            continue
        segments = list(prefix)
        while True:
            segments.append(tokens[pos])
            pos += 1
            if pos < len(tokens) and tokens[pos] == "::":
                pos += 1
                if tokens[pos] == "{":
                    inner, pos = parse_group(tokens, pos + 1, segments)
                    results += inner
                    segments = None
                    break
                continue
            break
        if segments is not None:
            alias = None
            if pos < len(tokens) and tokens[pos] == "as":
                alias = tokens[pos + 1]
                pos += 2
            results.append((segments, alias))
    return results, pos


def expand_import(text, table, report, where):
    tokens = re.findall(r'::|[{},]|"[^"]*"|[A-Za-z_][A-Za-z0-9_]*', text)
    if any(token.startswith('"') for token in tokens):
        report.warn(*where, f"#import of a file path is not translated: #import {text}")
        return []
    items, _ = parse_group(tokens, 0, [])
    lines = []
    for segments, alias in items:
        path = rename("::".join(segments), table, report)
        if segments[-1] in IMPORT_HAZARDS:
            report.warn(*where, f"{segments[-1]}: {IMPORT_HAZARDS[segments[-1]]}")
        lines.append(f"import {path}" + (f" as {alias}" if alias else "") + ";")
    return lines


def negate(expr):
    return expr[1:] if expr.startswith("!") else "!" + expr


def convert(text, table, path, report):
    lines = text.split("\n")
    body = []
    imports = []
    conds = []  # {"expr", "orig", "ctx", "declared", "line"}
    kinds = []  # the kind of each open brace: struct, fn, block
    paren = 0
    header = ""  # the code since the last `;`, `{` or `}`
    module = None

    def context():
        if paren > 0:
            return "params"
        return kinds[-1] if kinds else "top"

    def active():
        return [c["expr"] for c in conds if c["ctx"] not in STATEMENT]

    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        number = index + 1
        indent = raw[: len(raw) - len(raw.lstrip())]

        if stripped.startswith("#define_import_path"):
            module = stripped.split(None, 1)[1].strip().rstrip(";")
            index += 1
            continue

        if stripped.startswith("#import"):
            buf = strip_comment(stripped[len("#import"):]).strip()
            while buf.count("{") > buf.count("}"):
                index += 1
                buf += " " + strip_comment(lines[index]).strip()
            exprs = active()
            condition = " && ".join(exprs) if exprs else None
            for line in expand_import(buf.rstrip(";").strip(), table, report, (path, number)):
                imports.append((condition, line))
            index += 1
            continue

        match = re.match(r"#(ifdef|ifndef)\s+(\w+)", stripped)
        if match:
            expr = match.group(2) if match.group(1) == "ifdef" else "!" + match.group(2)
            cond = {"expr": expr, "ctx": context(), "declared": [], "line": number}
            conds.append(cond)
            if cond["ctx"] in STATEMENT:
                body.append(f"{indent}@if({expr}) {{")
            index += 1
            continue
        if re.match(r"#else\b", stripped) and not re.match(r"#else\s+\w", stripped):
            cond = conds[-1]
            cond["expr"] = negate(cond["expr"])
            if cond["ctx"] in STATEMENT:
                body.append(f"{indent}}} @else {{")
            index += 1
            continue
        if re.match(r"#endif\b", stripped):
            cond = conds.pop()
            if cond["ctx"] in STATEMENT:
                body.append(f"{indent}}}")
                if cond["declared"]:
                    report.warn(
                        path,
                        cond["line"],
                        "a conditional block declares "
                        + ", ".join(f"`{name}`" for name in cond["declared"])
                        + ": the braces end its scope, check that nothing after the block "
                        "uses them",
                    )
            index += 1
            continue
        if re.match(r"#(if|elif|define|undef)\b", stripped):
            report.warn(path, number, f"not translated: {stripped}")
            body.append(raw)
            index += 1
            continue

        # an ordinary line
        code = strip_comment(raw)
        if "/*" in code:
            report.warn(path, number, "block comment: the structure of the file may be misread")
        line = raw.replace("#{", "constants::{")
        line = re.sub(r"constants::\{(\w+)\}", r"constants::\1", line)
        line = re.sub(
            r"\b[A-Za-z_]\w*(?:::[A-Za-z_]\w*)+",
            lambda found: rename(found.group(0), table, report),
            line,
        )
        text_of_code = code.strip()
        where = context()
        names = [c["expr"] for c in conds if c["ctx"] == where]
        declared = re.match(r"(?:let|var|const)\s+(\w+)", text_of_code)
        if declared and where in STATEMENT:
            inner = [c for c in conds if c["ctx"] in STATEMENT]
            if inner:
                inner[-1]["declared"].append(declared.group(1))
        for pattern, message in CODE_HAZARDS:
            if re.search(pattern, code):
                report.warn(path, number, message)
        starts_item = text_of_code and not header.strip()
        closing = text_of_code.startswith(("}", ")"))
        if names and text_of_code:
            if (where == "top" and starts_item) or (
                where in ("struct", "params") and not closing
            ):
                line = f"{indent}@if({' && '.join(names)}) {line.lstrip()}"
        body.append(line)

        for char in code:
            if char == "{":
                kind = (
                    "struct"
                    if re.search(r"\bstruct\b", header)
                    else "fn"
                    if re.search(r"\bfn\b", header)
                    else "block"
                )
                kinds.append(kind)
                header = ""
            elif char == "}":
                if kinds:
                    kinds.pop()
                header = ""
            elif char == ";" and paren == 0:
                header = ""
            else:
                if char == "(":
                    paren += 1
                elif char == ")":
                    paren -= 1
                header += char
        index += 1

    if conds:
        report.warn(path, conds[-1]["line"], "an #ifdef is never closed")

    # imports go first, after the comment that opens the file
    split = 0
    while split < len(body) and body[split].lstrip().startswith("//"):
        split += 1
    seen = set()
    header_lines = []
    for condition, line in imports:
        if (condition, line) in seen:
            continue
        seen.add((condition, line))
        header_lines.append(f"@if({condition}) {line}" if condition else line)
    result = body[:split] + header_lines + ([""] if header_lines else []) + body[split:]
    return "\n".join(result), module


def own_modules(src, crate, files):
    """The modules of our shaders: the name each gives itself -> its path in `crate`."""
    table = {}
    for file in files:
        text = file.read_text()
        found = re.search(r"^#define_import_path\s+(\S+)", text, re.M)
        if found:
            relative = file.resolve().relative_to(src.resolve()).with_suffix("")
            table[found.group(1).rstrip(";")] = "::".join([crate, *relative.parts])
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--crate", default="client")
    parser.add_argument("--src", default="client/src")
    parser.add_argument("--delete", action="store_true", help="remove each .wgsl once translated")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    src = pathlib.Path(args.src)
    everything = sorted(src.rglob("*.wgsl"))
    files = [pathlib.Path(name) for name in args.files] or everything
    table = {**RENAMES, **own_modules(src, args.crate, everything)}
    report = Report()
    for file in files:
        text, module = convert(file.read_text(), table, str(file), report)
        target = file.with_suffix(".wesl")
        target.write_text(text if text.endswith("\n") else text + "\n")
        print(f"{file} -> {target}" + (f"  (was {module})" if module else ""))
        if args.delete:
            file.unlink()
    for warning in report.warnings:
        print(warning)
    if report.unverified:
        print("UNVERIFIED renames (check them against bevy_pbr 0.20): " + ", ".join(sorted(report.unverified)))
    sys.exit(1 if report.warnings else 0)


if __name__ == "__main__":
    main()
