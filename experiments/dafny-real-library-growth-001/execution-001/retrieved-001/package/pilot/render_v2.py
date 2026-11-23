"""Package-root renderer for the bounded runner; no authorization or execution.

This module is loaded by execution-001.runtime.load_renderer from its exact
staged path. It has no sibling/bare prepare import and returns Converse payloads.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

INPUTS = "pilot/draft-002/renderer-inputs.json"


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",", ":"),ensure_ascii=True,allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(value,message):
    if not value:
        raise ValueError(message)


def read(root,name):
    require(isinstance(name,str) and name and not name.startswith("/") and "\\" not in name
            and all(part not in {"",".",".."} for part in name.split("/")),"Unsafe renderer input path")
    path=root/name
    current=path
    while current!=root:
        require(not current.is_symlink(),"Renderer input symlink")
        current=current.parent
    require(path.is_file(),"Missing renderer input: "+name)
    return path.read_bytes()


def common(root):
    found={}
    for name in ("review_native","guard"):
        path=(root/"common"/(name+".py")).resolve()
        if name in sys.modules:
            module=sys.modules[name]
            require(Path(module.__file__).resolve()==path,"Mixed/stale common module: "+name)
        else:
            spec=importlib.util.spec_from_file_location(name,path)
            module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module
            try: spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(name,None)
                raise
        found[name]=module
    return found["guard"],found["review_native"]


def bundle(root):
    root=Path(root or Path(__file__).resolve().parent.parent).resolve()
    binding=json.loads(read(root,INPUTS))
    require(binding.get("schema")=="dafny-library-renderer-inputs-v2"
            and binding.get("authorization_issued") is False,"Unsupported renderer binding")
    for name,digest in binding["files"].items():
        require(sha(read(root,name))==digest,"Renderer input drift: "+name)
    require(sha(Path(__file__).read_bytes())==binding["renderer_sha256"],"Renderer code drift")
    scope=json.loads(read(root,binding["scope_path"]))
    return root,scope,binding


def stage_for(scope,project,chain_id,stage):
    matches=[slot for slot in scope["slots"] if slot["project"]==project
             and slot["chain_id"]==chain_id and slot["stage"]==stage]
    require(len(matches)==1,"Unknown/ambiguous lineage slot")
    return scope["projects"][project]["stages"][str(stage)],matches[0]


def sources_for(root,stage):
    sources={name:read(root,entry["path"]) for name,entry in stage["base_sources"].items()}
    require(all(sha(sources[name])==entry["sha256"] for name,entry in stage["base_sources"].items()),
            "Base source binding differs")
    return sources


def render_stage1(project,chain_id,*,root=None):
    root,scope,binding=bundle(root)
    stage,slot=stage_for(scope,project,chain_id,1)
    guard,native=common(root)
    edit=json.loads(read(root,stage["edit_profile"]))
    guard._profile(edit)
    sources=sources_for(root,stage)
    require(native.hashes(sources)==edit["base_source_sha256"],"Stage-one source/profile binding differs")
    payload=json.loads(read(root,stage["exact_payload_path"]))
    require(set(payload)=={"modelId","system","messages","inferenceConfig"},"Converse payload required")
    return dict(payload=payload,payload_sha256=sha(canonical(payload)),project=project,stage=1,
        stage_id=edit["stage_id"],chain_id=chain_id,slot_id=slot["id"],
        guard_profile_sha256=sha(canonical(edit)),source_revision_sha256=sha(canonical(native.hashes(sources))),
        source_bindings=native.hashes(sources),parent_audit=None,dispatch_eligible=False,authorization_issued=False)


def render_stage2(project,chain_id,parent_sources,parent_evidence,*,root=None,allow_synthetic=False):
    root,scope,binding=bundle(root)
    stage,slot=stage_for(scope,project,chain_id,2)
    guard,native=common(root)
    edit=json.loads(read(root,stage["edit_profile"]))
    guard._profile(edit)
    source_hashes=native.check_sources(parent_sources)
    parent_path=edit["parent_requirement"]["addition_path"]
    require(parent_path in source_hashes and
        {name:digest for name,digest in source_hashes.items() if name!=parent_path}==edit["base_source_sha256"],
        "Stage-two immutable parent source binding differs")
    audit=guard.validate_parent(edit,parent_sources,chain_id,parent_evidence,allow_synthetic=allow_synthetic)
    raw=parent_sources[parent_path]
    omitted=stage["parent_display_fixed_prefix_utf8"].encode()
    require(raw.startswith(omitted),"Accepted-parent fixed metadata prefix differs")
    parent_text=raw[len(omitted):].decode("utf-8",errors="strict")
    payload=json.loads(read(root,stage["child_template_payload_path"]))
    require(set(payload)=={"modelId","system","messages","inferenceConfig"},"Converse payload required")
    text=payload["messages"][0]["content"][0]["text"]
    placeholder="{{ACCEPTED_PARENT_SOURCE}}"
    require(text.count(placeholder)==1,"Ambiguous deferred parent position")
    payload["messages"][0]["content"][0]["text"]=text.replace(placeholder,parent_text,1)
    return dict(payload=payload,payload_sha256=sha(canonical(payload)),project=project,stage=2,
        stage_id=edit["stage_id"],chain_id=chain_id,slot_id=slot["id"],
        guard_profile_sha256=sha(canonical(edit)),source_revision_sha256=sha(canonical(source_hashes)),
        source_bindings=source_hashes,parent_audit=audit,parent_source_sha256=sha(raw),
        parent_view_sha256=sha(parent_text.encode()),omitted_fixed_metadata_bytes=len(omitted),
        synthetic=audit["synthetic"],dispatch_eligible=False,authorization_issued=False)
