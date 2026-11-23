"""Pure draft rendering; actual stage-two parents require common native replay.

A payload here is not authorization. Root's separately reviewed native release,
request budget and current ledger are prerequisites for any future dispatch.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys

from prepare import canonical, sha, require

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
PLACEHOLDER = "{{ACCEPTED_PARENT_SOURCE}}"


def common_api():
    """Use one exact class identity and reject stale/mixed module caches."""
    modules = {}
    for name in ("review_native", "guard"):
        path = (EXPERIMENT/"common"/(name+".py")).resolve()
        if name in sys.modules:
            module = sys.modules[name]
            require(Path(module.__file__).resolve() == path, "Mixed common module cache: " + name)
        else:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(name, None)
                raise
        modules[name] = module
    return modules["guard"], modules["review_native"]


def _read(root, path):
    require(isinstance(path, str) and path and not path.startswith("/")
            and ".." not in path.split("/") and "\\" not in path,
            "Unsafe draft artifact path")
    target = root/path
    require(target.is_file() and not any(p.is_symlink() for p in (target,*target.parents)),
            "Missing/symlink draft artifact")
    return target.read_bytes()


def bundle(root=None):
    root = Path(root or HERE/"draft-001").resolve()
    manifest = json.loads(_read(root,"draft-manifest.json"))
    require(manifest["schema"] == "dafny-library-prompt-draft-manifest-v1",
            "Unsupported prompt manifest")
    require(manifest["status"] == "DRAFT_PENDING_NATIVE_GATES"
            and manifest["authorization_issued"] is False
            and manifest["qualification_release"] is None, "Unexpected draft authority")
    for path,digest in manifest["files"].items():
        require(sha(_read(root,path)) == digest, "Draft artifact drift: " + path)
    for name,digest in manifest["code_sha256"].items():
        require(name in {"prepare.py","render.py"} and sha((HERE/name).read_bytes()) == digest,
                "Draft renderer/preparer drift")
    inputs = json.loads(_read(root,"input-pins.json"))["experiment_relative_files"]
    for name,digest in inputs.items():
        require(sha(_read(EXPERIMENT,name)) == digest, "Source/common input drift: " + name)
    scope = json.loads(_read(root,"scope.json"))
    require(scope["execution_enabled"] is False and scope["qualification_release"] is None,
            "Draft cannot issue execution release")
    return root,scope


def _slot(scope, project, chain_id, stage):
    matches = [slot for slot in scope["slots"] if slot["project"]==project
               and slot["chain_id"]==chain_id and slot["stage"]==stage]
    require(len(matches)==1, "Unknown or ambiguous fixed slot")
    return matches[0]


def _base_sources(root, scope, project):
    manifest = json.loads(_read(root,scope["projects"][project]["base_sources_manifest"]))
    sources = {path:_read(EXPERIMENT,manifest["workspace_root"]+"/"+path)
               for path in manifest["source_sha256"]}
    require({path:sha(raw) for path,raw in sources.items()} == manifest["source_sha256"],
            "Base source snapshot drift")
    return sources


def render_stage1(project, chain_id, *, root=None):
    root,scope = bundle(root)
    slot = _slot(scope,project,chain_id,1)
    stage = scope["projects"][project]["stages"]["1"]
    profile = json.loads(_read(root,stage["edit_profile_path"]))
    guard,native = common_api()
    guard._profile(profile)
    sources = _base_sources(root,scope,project)
    require(native.hashes(sources) == profile["base_source_sha256"], "Stage-one source/profile mismatch")
    payload = json.loads(_read(root,stage["exact_payload_path"]))
    require(PLACEHOLDER not in canonical(payload).decode(), "Stage-one payload has deferred content")
    return dict(payload=payload,payload_sha256=sha(canonical(payload)),project=project,stage=1,
                stage_id=stage["stage_id"],chain_id=chain_id,slot_id=slot["id"],
                guard_profile_sha256=sha(canonical(profile)),
                source_revision_sha256=sha(canonical(native.hashes(sources))),
                source_bindings=native.hashes(sources),parent_audit=None,
                dispatch_eligible=False,authorization_issued=False)


def render_stage2(project, chain_id, parent_sources, parent_evidence, *, root=None,
                  allow_synthetic=False):
    root,scope = bundle(root)
    slot = _slot(scope,project,chain_id,2)
    stage = scope["projects"][project]["stages"]["2"]
    profile = json.loads(_read(root,stage["edit_profile_path"]))
    guard,native = common_api()
    guard._profile(profile)
    source_hashes = native.check_sources(parent_sources)
    parent_path = profile["parent_requirement"]["addition_path"]
    require(parent_path in source_hashes and
            {path:digest for path,digest in source_hashes.items() if path!=parent_path}
            == profile["base_source_sha256"], "Wrong immutable parent source map")
    parent_audit = guard.validate_parent(profile,parent_sources,chain_id,parent_evidence,
                                         allow_synthetic=allow_synthetic)
    first = scope["projects"][project]["stages"]["1"]
    first_profile = json.loads(_read(root,first["edit_profile_path"]))
    raw_parent = parent_sources[parent_path]
    # Remove only the exact fixed metadata prefix omitted from stage-one view.
    # All accepted body bytes remain unchanged, including arbitrary comments.
    display_audit = json.loads(_read(root,"template-audits/"+project+"-stage1.json"))
    omitted = display_audit.get("model_display_excludes_leading_metadata_bytes",0)
    fixed_prefix = first_profile["addition"]["template_utf8"].encode()[:omitted]
    require(raw_parent[:omitted] == fixed_prefix, "Accepted parent fixed metadata differs")
    parent_text = raw_parent[omitted:].decode("utf-8",errors="strict")
    payload = json.loads(_read(root,stage["child_template_payload_path"]))
    text = payload["body"]["messages"][0]["content"][0]["text"]
    require(text.count(PLACEHOLDER)==1, "Deferred parent position ambiguous")
    payload["body"]["messages"][0]["content"][0]["text"] = text.replace(PLACEHOLDER,parent_text,1)
    return dict(payload=payload,payload_sha256=sha(canonical(payload)),project=project,stage=2,
                stage_id=stage["stage_id"],chain_id=chain_id,slot_id=slot["id"],
                guard_profile_sha256=sha(canonical(profile)),
                source_revision_sha256=sha(canonical(source_hashes)),source_bindings=source_hashes,
                parent_audit=parent_audit,parent_view_sha256=sha(parent_text.encode()),
                parent_source_sha256=sha(raw_parent),omitted_fixed_metadata_bytes=omitted,
                dispatch_eligible=False,authorization_issued=False,
                synthetic=bool(parent_audit["synthetic"]))
