"""Deterministic, offline construction of the DynamicArray source controls.

This never executes Dafny, a model, or a network command. Existing outputs are
checked byte-for-byte, never silently replaced.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMIT = "fcb2042d6d043a2634f0854338c08feeaaaf4ae2"
UPSTREAM = "Source/DafnyStandardLibraries/src/Std/"
BASE_FILES = [UPSTREAM + name + ".dfy" for name in ("BoundedInts", "Wrappers", "DynamicArray")]
APPEND = "growth/AppendAll.dfy"
ROTATE = "growth/AppendRotated.dfy"
APPEND_TARGET = "RepoDiscoStdAppend.AppendAll"
ROTATE_TARGET = "RepoDiscoStdRotate.AppendRotated"
BEGIN = "    // BEGIN REPLACEMENT\n"
END = "    // END REPLACEMENT\n"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def fixed_parts(name, root=ROOT):
    raw = (root / "templates" / name).read_text()
    require(raw.count(BEGIN) == raw.count(END) == 1, "Unique protected body boundary required")
    before, after = raw.split(BEGIN)
    middle, after = after.split(END)
    require(middle == "", "Template must contain no supplied body")
    return before + BEGIN, END + after


def reconstruct(name, body, root=ROOT):
    before, after = fixed_parts(name, root)
    value = (root / "bodies" / (body + ".txt")).read_text()
    require(not value or value.endswith("\n"), "Body must end with newline")
    require(BEGIN not in value and END not in value, "Body cannot move its boundary")
    return (before + value + after).encode()


def upstream_sources(root=ROOT):
    manifest = json.loads((root / "upstream/source-manifest.json").read_bytes())
    require(manifest["repository"] == "dafny-lang/dafny" and manifest["commit"] == COMMIT and
            manifest["tag"] == "v4.11.0", "Wrong release snapshot")
    pins = {entry["path"]: entry for entry in manifest["files"]}
    # All seven saved artifacts are provenance; exactly these three sources form
    # the verified module dependency closure, not the entire standard library.
    for name, entry in pins.items():
        raw = (root / "upstream" / name).read_bytes()
        require(sha(raw) == entry["sha256"] and len(raw) == entry["bytes"], "Upstream bytes changed: " + name)
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest() == entry["git_blob_sha"],
                "Git blob identity differs: " + name)
    return {name: (root / "upstream" / name).read_bytes() for name in BASE_FILES}


def specification():
    # id, stage, stage-one body, stage-two body, result, failed, passed, omitted
    return [
        ("baseline", 0, None, None, "PROOF_PASS", [], [], []),
        ("append-reference", 1, "append-reference", None, "PROOF_PASS", [], [APPEND_TARGET], []),
        ("append-alternative", 1, "append-alternative", None, "PROOF_PASS", [], [APPEND_TARGET], []),
        ("append-empty", 1, "append-empty", None, "PROOF_FAILURE", [APPEND_TARGET], [], []),
        ("append-reverse", 1, "append-reverse", None, "PROOF_FAILURE", [APPEND_TARGET], [], []),
        ("rotate-reference", 2, "append-reference", "rotate-reference", "PROOF_PASS", [], [APPEND_TARGET, ROTATE_TARGET], []),
        ("rotate-direct", 2, "append-reference", "rotate-direct", "PROOF_PASS", [], [APPEND_TARGET, ROTATE_TARGET], []),
        ("rotate-empty", 2, "append-reference", "rotate-empty", "PROOF_FAILURE", [ROTATE_TARGET], [APPEND_TARGET], []),
        ("rotate-original-order", 2, "append-reference", "rotate-original-order", "PROOF_FAILURE", [ROTATE_TARGET], [APPEND_TARGET], []),
        ("rotate-unproved-append", 2, "append-empty", "rotate-reference", "PROOF_FAILURE", [APPEND_TARGET], [ROTATE_TARGET], []),
        ("append-omitted", 1, "append-empty", None, "COVERAGE_OMISSION", [], [], [APPEND_TARGET]),
        ("rotate-omitted", 2, "append-reference", "rotate-empty", "COVERAGE_OMISSION", [], [APPEND_TARGET], [ROTATE_TARGET]),
    ]


def material(root=ROOT):
    old = upstream_sources(root)
    files = {}
    cases = []
    for ident, stage, parent, child, expected, failed, passed, omitted in specification():
        sources = dict(old)
        if parent is not None:
            sources[APPEND] = reconstruct("AppendAll.dfy", parent, root)
        if child is not None:
            sources[ROTATE] = reconstruct("AppendRotated.dfy", child, root)
        scope = BASE_FILES + ([APPEND] if stage >= 1 else []) + ([ROTATE] if stage == 2 else [])
        missing_paths = [APPEND] if ident == "append-omitted" else [ROTATE] if ident == "rotate-omitted" else []
        commands = [name for name in scope if name not in missing_paths]
        required = ([APPEND_TARGET] if stage >= 1 else []) + ([ROTATE_TARGET] if stage == 2 else [])
        prefix = "cases/" + ident + "/"
        files.update({prefix + name: raw for name, raw in sources.items()})
        cases.append(dict(id=ident, workspace_dir="cases/" + ident, stage=stage,
                          command_files=commands, declared_scope_files=scope,
                          expected_category=expected,
                          expected_native_category="PROOF_FAILURE" if expected == "PROOF_FAILURE" else "PROOF_PASS",
                          expected_failed_targets=failed, expected_passed_targets=passed,
                          required_targets=required, omitted_targets=omitted,
                          omit_from_command=missing_paths,
                          source_sha256={name: sha(raw) for name, raw in sorted(sources.items())},
                          analyst_authored=True, model_acceptance=False, native_status="UNKNOWN",
                          actual_native_unit_labels=None,
                          classification_requires_named_units_and_exact_inventory=True))
    files["cases.json"] = encode(cases)
    return files


def build(root=ROOT):
    files = material(root)
    for name, raw in files.items():
        path = root / name
        if path.exists():
            require(path.is_file() and path.read_bytes() == raw, "Existing construction differs: " + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(raw)
    return dict(cases=12, source_files=len(files) - 1, model_calls=0, native_calls=0,
                native_status="UNKNOWN", material_sha256={name: sha(raw) for name, raw in sorted(files.items())})


if __name__ == "__main__":
    value = build()
    print(json.dumps({key: item for key, item in value.items() if key != "material_sha256"}, indent=2, sort_keys=True))
