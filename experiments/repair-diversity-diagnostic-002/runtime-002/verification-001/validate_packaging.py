"""Reproduce manifest-only staging and six offline guard/source tests; no Dafny."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent
TESTS=[
 'test_design.DiagnosticTests.test_exact_rebuild_and_original_frozen_guard_replay',
 'test_design.DiagnosticTests.test_edits_touch_only_exact_initial_statements_and_keep_call_order',
 'test_design.DiagnosticTests.test_separate_candidates_apply_same_edit_to_both_existing_bodies',
 'test_design.DiagnosticTests.test_unexpected_edit_location_is_rejected',
 'test_design.DiagnosticTests.test_guard_rejects_bypasses_and_protected_parent_edits',
 'test_design.DiagnosticTests.test_diagnostic_categories_require_coherent_strict_evidence',
]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())
def validate(root=ROOT):
    pins=load(root/'manifest.json');frozen=load(root/'frozen-001/freeze.json')
    required={'frozen-001/'+name:h for name,h in frozen['files'].items()}
    required['frozen-001/freeze.json']=sha(root/'frozen-001/freeze.json')
    assert all(pins.get(name)==h for name,h in required.items()),'Manifest omits a frozen dependency'
    assert 'frozen-001/policy/README.md' in required
    for name,h in pins.items():
        p=Path(name);assert not p.is_absolute() and '..' not in p.parts
        assert sha(root/name)==h,name
    with tempfile.TemporaryDirectory(prefix='repair-diagnostic-stage-') as tmp:
        stage=Path(tmp)/'runtime-002';stage.mkdir()
        for name in [*pins,'manifest.json']:
            dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,dest)
        assert {x.relative_to(stage).as_posix() for x in stage.rglob('*') if x.is_file()}==set(pins)|{'manifest.json'}
        for name,h in pins.items():assert sha(stage/name)==h,name
        process=subprocess.run([sys.executable,'-B','-m','unittest',*TESTS,'-v'],cwd=stage,capture_output=True,text=True,timeout=60)
        print(process.stdout,end='');print(process.stderr,end='')
        if process.returncode:raise RuntimeError('Manifest-only staged offline tests failed; preserve this log')
        for name,h in pins.items():assert sha(stage/name)==h,name
    return dict(manifest_sha256=sha(root/'manifest.json'),manifest_files=len(pins),frozen_files_included=len(required),
                staged_offline_tests_passed=len(TESTS),copied_only_manifest_entries=True,
                original_proof_semantics_unchanged=True,model_calls=0,dafny_invocations=0)
if __name__=='__main__':print(json.dumps(validate(),indent=2))
