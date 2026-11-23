"""Package-root renderer for the bounded runner; no authorization or execution.

This module is loaded by execution-001.runtime.load_renderer from its exact
staged path. It has no sibling/bare prepare import and returns Converse payloads.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

INPUTS = "pilot/frozen-001/renderer-inputs.json"


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
    require(binding.get("schema")=="dafny-library-independent-renderer-inputs-v1"
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

