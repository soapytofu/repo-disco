"""Construct three source-bound AWS baseline/reference workspaces offline.

No verifier, model, network, credential or subprocess operations are used.
Output is exclusive; native outcomes are deliberately UNKNOWN.
"""
from pathlib import Path
import hashlib
import json
import posixpath
import re

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "upstream"
ANCHORS = [
    "StandardLibrary/src/UInt.dfy",
    "StandardLibrary/src/UTF8.dfy",
    "AwsCryptographicMaterialProviders/dafny/AwsCryptographicMaterialProviders/src/CanonicalEncryptionContext.dfy",
]
STAGE1 = "StandardLibrary/src/RepoDiscoU16Frame.dfy"
STAGE2 = "AwsCryptographicMaterialProviders/dafny/AwsCryptographicMaterialProviders/src/RepoDiscoContextEntry.dfy"
INCLUDES = re.compile(r'^\s*include\s+"([^"]+)"', re.M)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()


def pinned_inventory():
    pins = {}
    receipt_hashes = {}
    for prefix, name in [("", "aws-001.json"), ("libraries/", "libraries-001.json")]:
        p = HERE.parent / "source-acquisition" / name
        data = p.read_bytes()
        receipt_hashes[name] = digest(data)
        for row in json.loads(data)["files"]:
            pins[prefix + row["path"]] = row
    return pins, receipt_hashes


def closure(anchors):
    todo = list(anchors)
    seen = set()
    edges = {}
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        if name.startswith("../") or name.startswith("/"):
            raise ValueError("Include escaped workspace: " + name)
        seen.add(name)
        p = UPSTREAM / name
        if not p.is_file() or p.is_symlink():
            raise ValueError("Missing/nonregular include: " + name)
        deps = [
            posixpath.normpath(posixpath.join(posixpath.dirname(name), v))
            for v in INCLUDES.findall(p.read_text())
        ]
        edges[name] = deps
        todo.extend(deps)
    return sorted(seen), edges


def main():
    pins, receipts = pinned_inventory()
    original_roots, edges = closure(ANCHORS)
    originals = {}
    for name in original_roots:
        data = (UPSTREAM / name).read_bytes()
        row = pins[name]
        if len(data) != row["bytes"] or digest(data) != row["sha256"] or git_blob(data) != row["git_blob_sha"]:
            raise ValueError("Upstream source drift: " + name)
        originals[name] = data
    additions = {name: (HERE / "draft" / "overlay" / name).read_bytes() for name in [STAGE1, STAGE2]}
    out = HERE / "cases-001"
    out.mkdir(exist_ok=False)
    cases = []
    for case_id, new_names, targets in [
        ("aws-baseline-001", [], []),
        ("aws-stage1-reference-001", [STAGE1], ["RepoDiscoU16Frame.ReadU16Frame"]),
        ("aws-stage2-reference-001", [STAGE1, STAGE2], ["RepoDiscoU16Frame.ReadU16Frame", "RepoDiscoContextEntry.ReadContextEntry"]),
    ]:
        workspace = out / case_id / "workspace"
        workspace.mkdir(parents=True)
        contents = dict(originals)
        contents.update({name: additions[name] for name in new_names})
        file_rows = []
        for name, data in sorted(contents.items()):
            destination = workspace / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            file_rows.append({
                "path": name, "bytes": len(data), "sha256": digest(data),
                "origin": "analyst-reference" if name in additions else "pinned-upstream",
                "git_blob_sha": None if name in additions else pins[name]["git_blob_sha"],
            })
        for name in contents:
            for include in INCLUDES.findall(contents[name].decode()):
                dependency = posixpath.normpath(posixpath.join(posixpath.dirname(name), include))
                if dependency not in contents:
                    raise ValueError("Case closure incomplete: " + dependency)
        row = {
            "id": case_id,
            "workspace": str(workspace.relative_to(HERE)),
            "kind": "unchanged-upstream-baseline" if not new_names else "analyst-reference",
            "expected_native_outcome": "PASS",
            "observed_native_outcome": "UNKNOWN",
            "new_targets_provisional": targets,
            "explicit_root_files": sorted(contents),
            "source_files": file_rows,
            "counts": {"upstream_sources": len(originals), "additions": len(new_names)},
        }
        (out / case_id / "case.json").write_text(json.dumps(row, indent=2) + "\n")
        cases.append(row)
    manifest = {
        "schema": "repodisco-aws-native-reference-cases-v1",
        "status": "PREPARED_NATIVE_UNKNOWN",
        "source_anchors": ANCHORS,
        "original_explicit_roots": original_roots,
        "include_edges": edges,
        "upstream_receipts_sha256": receipts,
        "cases": cases,
        "native_policy": {
            "required_verifier": "4.9.1",
            "cores": 1,
            "function_syntax": 3,
            "unicode_char": False,
            "enforce_determinism": True,
            "allow_deprecation": True,
            "allow_external_contracts": True,
            "resource_and_wall_limits": "Root must select/freeze before dispatch; source-derived component limits documented in DESIGN.md.",
        },
        "trust_scope": "Dependency-closed selected sources, all listed as explicit roots; no full AWS repository claim. Existing extern/axiom/unlogged definitions remain explicit.",
        "new_model_calls": 0,
        "native_calls": 0,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "status": "OFFLINE_CASE_CONSTRUCTION_COMPLETE",
        "original_sources": len(originals),
        "original_source_bytes": sum(map(len, originals.values())),
        "case_ids": [c["id"] for c in cases],
        "case_source_counts": [len(c["source_files"]) for c in cases],
        "native_outcomes": "UNKNOWN",
        "native_calls": 0, "model_calls": 0,
    }, indent=2))


if __name__ == "__main__":
    main()

