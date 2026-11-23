"""Saved-evidence replay and synthetic failure boundaries; no native/API calls."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

import native_failure_policy as policy
import native_host as h
import runtime as r
import test_native_host as fixtures
import test_runner as runner_fixtures

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OLD_SLOT = REPO / 'experiments/real-repository-growth-001/execution-004/retrieved-001/model-001/slot-01'


def load_saved():
    pins = r.read(ROOT/'resource-evidence-inputs.json')['files']
    for name, digest in pins.items():
        if h.file_sha(REPO/name) != digest:
            raise ValueError('Historical resource fixture changed')
    api = h.protocol_api(REPO)
    value = r.read(OLD_SLOT/'native/native-binding.json')
    value['artifact_sha256'] = tuple(tuple(pair) for pair in value['artifact_sha256'])
    binding = api.NativeBinding(**value)
    artifacts = {name: (OLD_SLOT/'evidence'/name).read_bytes() for name, _ in binding.artifact_sha256}
    source_map = r.read(OLD_SLOT/'source-manifest.json')['source_sha256']
    upstream = REPO/'experiments/real-repository-qualification-001/upstream/dafny-vmc'
    sources = {name: ((OLD_SLOT/'source-overlay'/name) if name.startswith('repodisco-growth/') else upstream/name).read_bytes()
               for name in source_map}
    if api.b.source_hashes(sources) != source_map:
        raise ValueError('Historical source map differs')
    return binding, artifacts, sources, r.read(OLD_SLOT/'native/native-units.json')


def rebind_synthetic(base, raw_changes, record_changes=None):
    """TEST ONLY: repair synthetic hash links, never authenticate real evidence."""
    assert base.synthetic
    artifacts = dict(base.artifacts)
    artifacts.update(raw_changes)
    record = json.loads(artifacts['record.json'])
    record.update(record_changes or {})
    record.update(exit_code=4, outer_timeout=False, timeout=False, resource_capture_missing=False)
    record['artifacts'] = {name: h.sha(artifacts[name]) for name in ('stdout.txt','stderr.txt','resources.txt')}
    bound = json.loads(artifacts['bound-record.json'])
    bound['exit_code'] = 4
    bound['raw_sha256'] = {name: h.sha(artifacts[name]) for name in bound['raw_sha256']}
    artifacts['record.json'] = h.canonical(record)
    artifacts['bound-record.json'] = h.canonical(bound)
    binding = replace(base.binding, artifact_sha256=tuple(sorted((name,h.sha(raw)) for name,raw in artifacts.items())))
    return binding, artifacts


def synthetic_resource(slot, sources, repo, run_id):
    base = fixtures.fixture_result(slot, sources, repo, run_id=run_id, outcome='proof_failure')
    scope = json.loads(base.artifacts['scope.json'])
    failed = [row['name'] for row in base.extraction['rows'] if row['status']=='Failed']
    assert len(failed) == 1
    stage = h.protocol_api(repo).b.stage_spec(slot['stage_id'])[0]
    csv_name = next(name for name in base.artifacts if name.startswith('csv/'))
    text = '\n'.join(scope['upstream_warnings'])+'\n'
    text += f"{stage['path']}(1,0): Verification out of resource ({failed[0]})\n"
    text += f"Dafny program verifier finished with {len(base.extraction['rows'])-1} verified, 0 errors, 1 out of resource\n"
    text += 'Results File: /synthetic/workspace/'+csv_name[4:]+'\n'
    binding, artifacts = rebind_synthetic(base, {'stdout.txt':text.encode(),
        'resources.txt':b'SYNTHETIC TEST ONLY; NO PROCESS RAN\n\tSignals delivered: 0\n\tExit status: 4\n'})
    extraction = h.audit_candidate_native(binding, artifacts, sources, repo, allow_synthetic=True)
    classification, terminal = h.classify(extraction)
    return replace(base, binding=binding, artifacts=artifacts, extraction=extraction,
                   classification=classification, terminal=terminal)


class ResourcePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding, cls.artifacts, cls.sources, cls.old = load_saved()
        cls.current = h.audit_candidate_native(cls.binding, cls.artifacts, cls.sources, REPO)

    def test_exact_saved_native_replay_is_unaccepted_not_rescoring(self):
        current = copy.deepcopy(self.current)
        receipt = current.pop('completed_resource_outcome')
        self.assertEqual(current, self.old)
        self.assertTrue(receipt['eligible'])
        self.assertEqual((receipt['verified_units'], receipt['resource_failed_units'], receipt['required_units']), (267,1,268))
        self.assertEqual(receipt['failed_units'], ['RepoDiscoGrowthShift.MoveToFront (well-formedness)'])
        self.assertFalse(receipt['permits_parent'])
        self.assertFalse(receipt['original_parser_count_agreement'])
        self.assertEqual(h.classify(self.current), ('BOUNDED_NATIVE_RESOURCE_FAILURE',False))
        self.assertEqual(h.classify(self.old), ('TERMINAL_NATIVE_VERIFIER_RESOURCE_FAILURE',True))

    def check_rejected(self, extraction, artifacts, reason):
        receipt = policy.audit(extraction, artifacts)
        self.assertFalse(receipt['eligible'])
        self.assertEqual(receipt['reason'], reason)
        self.assertTrue(h.classify(dict(extraction,completed_resource_outcome=receipt))[1])

    def text_case(self, stdout=None, stderr=None, resources=None):
        artifacts = dict(self.artifacts); extraction = copy.deepcopy(self.old)
        for name, data in [('stdout.txt',stdout),('stderr.txt',stderr),('resources.txt',resources)]:
            if data is not None:
                artifacts[name] = data
                extraction['raw_sha256'][name] = h.sha(data)
        # These intentionally synthetic mutations test the classifier boundary;
        # the production host additionally replays the complete native binding.
        return extraction, artifacts

    def test_unbound_raw_change_rejected(self):
        artifacts = dict(self.artifacts, **{'stdout.txt':self.artifacts['stdout.txt']+b'changed'})
        self.check_rejected(self.old, artifacts, 'raw_hash_drift')
        with self.assertRaises(ValueError):
            h.audit_candidate_native(self.binding, artifacts, self.sources, REPO)

    def test_changed_source_rejected_before_failure_classification(self):
        sources = dict(self.sources)
        name = 'repodisco-growth/MoveToFront.dfy'
        sources[name] += b'\n'
        with self.assertRaises(ValueError):
            h.audit_candidate_native(self.binding, self.artifacts, sources, REPO)

    def test_process_limits_missing_resources_and_wrong_project_remain_terminal(self):
        for name, value in [('timeout',True),('outer_timeout',True),('resource_capture_missing',True),('attempts',2)]:
            with self.subTest(name=name):
                extraction = copy.deepcopy(self.old); extraction['native_execution'][name]=value
                self.check_rejected(extraction,self.artifacts,'incomplete_process_or_resources')
        extraction = copy.deepcopy(self.old); extraction['project']='vest'
        self.check_rejected(extraction,self.artifacts,'unsupported_project')

    def test_missing_or_repeated_inventory_rejected(self):
        extraction = copy.deepcopy(self.old); extraction['coverage_complete']=False
        self.check_rejected(extraction,self.artifacts,'unqualified_source_or_inventory')
        extraction = copy.deepcopy(self.old); extraction['rows']=extraction['rows'][:-1]
        self.check_rejected(extraction,self.artifacts,'row_inventory_mismatch')
        extraction = copy.deepcopy(self.old); extraction['rows'][0]['status']='Unknown'
        self.check_rejected(extraction,self.artifacts,'unknown_unit_status')

    def test_summary_missing_duplicated_inconsistent_or_proof_errors_rejected(self):
        old = self.artifacts['stdout.txt']
        summary = b'Dafny program verifier finished with 267 verified, 0 errors, 1 out of resource'
        for new, reason in [(b'', 'resource_summary_count_mismatch'),
                            (summary+b'\n'+summary,'resource_summary_count_mismatch'),
                            (summary.replace(b'267',b'266'),'resource_summary_count_mismatch'),
                            (summary.replace(b'0 errors',b'1 errors'),'unrecognized_stdout_diagnostic')]:
            with self.subTest(summary=new):
                self.check_rejected(*self.text_case(stdout=old.replace(summary,new)),reason)

    def test_named_failure_must_match_csv_and_bound_source(self):
        raw = self.artifacts['stdout.txt']
        self.check_rejected(*self.text_case(stdout=raw.replace(b'(RepoDiscoGrowthShift.MoveToFront (well-formedness))',b'(Other.Unit)')),
                            'failed_unit_diagnostics_mismatch')
        self.check_rejected(*self.text_case(stdout=raw.replace(b'repodisco-growth/MoveToFront.dfy(6,2)',b'absent.dfy(6,2)')),
                            'diagnostic_source_missing')

    def test_stderr_oom_timeout_and_unknown_stdout_are_not_contained(self):
        for extra in [b'out of memory\n',b'solver timeout\n',b'Internal verifier error\n',b'Environment failed\n']:
            with self.subTest(extra=extra):
                self.check_rejected(*self.text_case(stdout=self.artifacts['stdout.txt']+extra), 'unrecognized_stdout_diagnostic')
        self.check_rejected(*self.text_case(stderr=b'out of memory\n'),'nonempty_stderr')

    def test_warning_profile_and_resource_completion_are_required(self):
        extraction = copy.deepcopy(self.old); extraction['warning_review']['no_additional_warnings']=False
        self.check_rejected(extraction,self.artifacts,'warning_profile_differs')
        extraction = copy.deepcopy(self.old); extraction['warning_review']['upstream_warning_profile_complete']=False
        self.check_rejected(extraction,self.artifacts,'warning_profile_differs')
        self.check_rejected(*self.text_case(resources=b'NATIVE_RESOURCE_CAPTURE_MISSING\n'),'resource_completion_record_missing')
        self.check_rejected(*self.text_case(resources=self.artifacts['resources.txt'].replace(b'Exit status: 4',b'Exit status: 137')),
                            'resource_completion_record_missing')

    def test_results_file_and_scope_hash_must_match(self):
        self.check_rejected(*self.text_case(stdout=self.artifacts['stdout.txt'].replace(b'Results File: /n/',b'Results File: /changed/')),
                            'csv_results_path_mismatch')
        artifacts = dict(self.artifacts, **{'scope.json':b'{}'})
        self.check_rejected(self.old,artifacts,'metadata_hash_drift')

    def test_passing_extractions_remain_byte_exact(self):
        value = dict(native_category='PROVED',qualified_pass=True)
        self.assertIs(policy.attach(value,{}), value)


class ResourceDispatchTests(unittest.TestCase):
    def test_completed_resource_failure_blocks_child_continues_other_lineages_and_replays(self):
        fixture = runner_fixtures.RunnerTests('test_one_failed_parent_blocks_its_exact_child_and_other_lineages_continue')
        fixture.setUpClass(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        class Native(runner_fixtures.FakeNative):
            def verify(self,slot,sources,destination,run_id):
                if slot['slot_id']=='slot-01':
                    self.calls.append(slot['slot_id'])
                    return synthetic_resource(slot,sources,REPO,run_id)
                return super().verify(slot,sources,destination,run_id)
        native = Native()
        result = fixture.run_sim(verifier=native)
        self.assertEqual(result['status'],'SYNTHETIC_COMPLETE')
        self.assertEqual(result['transport_reservations'],7)
        self.assertEqual(result['blocked_children'],['slot-03'])
        self.assertEqual(result['completed_lineages'],3)
        self.assertNotIn('slot-03',native.calls)
        self.assertEqual(len(native.calls),7)
        self.assertFalse((fixture.out/'accepted-heads/vmc-lineage-01.json').exists())
        rows = r.read(fixture.out/'results.json')
        self.assertEqual(rows[0]['outcome'],'BOUNDED_NATIVE_RESOURCE_FAILURE')
        self.assertFalse(rows[0]['qualified_pass'])
        import review
        replay = review.review_run(REPO,fixture.out,allow_synthetic=True,expected_package=fixture.package)
        self.assertTrue(replay['experiment_complete'])
        self.assertEqual(replay['accepted_stages'],6)


if __name__ == '__main__':
    unittest.main()
