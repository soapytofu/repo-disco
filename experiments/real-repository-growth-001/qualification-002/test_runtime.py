"""Synthetic parser/worker checks only; never starts a native verifier or SSH."""
import copy
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import common as c
from capture import digest, write
from gates.vmc import protocol as dg
from score import observe
from verify_references import files, make_command, profile_for, remote_qualification, verify_one, tool_observation
from review import review_verification


def dafny_raw(*, removed=(), failed=(), extra=(), warnings=None, exit_code=None):
    base = c.base_profile('dafny-vmc')
    names = sorted(set(base['required_units']) | set(c.reference('dafny-vmc')['required_new_names']) | set(extra))
    names = [n for n in names if n not in removed]
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(base['csv_header'])
    for n in names:
        writer.writerow([n, 'Failed' if n in failed else 'Passed', '00:00:00.010', '1'])
    errors = sum(n in failed for n in names)
    wrn = base['upstream_warnings'] if warnings is None else warnings
    stdout = ('\n'.join(wrn) + '\nDafny program verifier finished with %d verified, %d errors\n' %
              (len(names) - errors, errors)).encode()
    return dict(exit_code=(4 if errors else 2) if exit_code is None else exit_code,
                command=['synthetic-dafny']), {'stdout.txt': stdout, 'stderr.txt': b'',
                'resources.txt': b'synthetic CPU/resource record\n', 'csv/TestResults/fake.csv': output.getvalue().encode()}




def freeze_test_root(root):
    pins = files(root)
    pins.pop('runtime-freeze.json', None)
    write(root / 'runtime-freeze.json', dict(model_calls=0, native_invocations=1, controls_released=False, files=pins))


class ScopeAndScorerTests(unittest.TestCase):
    def test_catalog_has_exactly_one_dafny_reference(self):
        plan = c.validate_inputs()
        self.assertEqual(sum(len(x) for x in plan['catalog'].values()), 1)
        self.assertEqual(c.PROJECTS, ('dafny-vmc',))
        self.assertEqual(plan['native_invocations_authorized_in_this_runtime'], 1)
        self.assertFalse(plan['old_model_body_policy_compatible'])
        self.assertEqual(plan['excluded_projects'], ['vest'])
        with self.assertRaisesRegex(ValueError, 'not executable'):
            c.reference('dafny-vmc', case_id='move-reference')
        with self.assertRaisesRegex(ValueError, 'Unknown project'):
            c.reference('vest')

    def test_command_binds_unchanged_fixed_budget_and_full_scope(self):
        cmd, logical, limit, base = make_command('dafny-vmc', Path('/tmp/work-dafny'))
        self.assertEqual(limit, 300)
        self.assertEqual(logical[logical.index('--resource-limit') + 1], '100000')
        self.assertTrue(set(base['explicit_sources']) <= set(logical))
        self.assertTrue(set(c.reference('dafny-vmc')['overlay_sha256']) <= set(logical))

    def test_old_namespace_obligations_cannot_qualify_revised_reference(self):
        current = c.reference('dafny-vmc')['required_new_names']
        old = [n.replace('RepoDiscoGrowthShift.', 'FisherYates.GrowthShift.')
                .replace('RepoDiscoGrowthPick.', 'FisherYates.GrowthPick.') for n in current]
        n, raw = dafny_raw(removed=current, extra=old)
        observation = observe('dafny-vmc', n, raw)
        self.assertFalse(observation['coverage_complete'])
        self.assertEqual(observation['growth_inventory_review']['missing_new'], sorted(current))
        self.assertEqual(observation['growth_inventory_review']['unexpected_new'], sorted(old))

    def test_vest_has_no_worker_tool_or_command_path(self):
        with self.assertRaisesRegex(ValueError, 'Unknown project'):
            make_command('vest', Path('/tmp/never-created'))
        with self.assertRaisesRegex(ValueError, 'Unknown project'):
            tool_observation('vest')
        with self.assertRaisesRegex(ValueError, 'Unknown project'):
            verify_one('vest', Path('/tmp/never-created'), '12345')
        self.assertFalse((c.ROOT / 'verify-vest.sbatch').exists())
        self.assertFalse((c.ROOT / 'inputs/vest').exists())

    def test_source_revision_bound_to_namespace_only_freeze(self):
        profile = profile_for('dafny-vmc')
        plan = c.read(c.ROOT / 'plan.json')
        self.assertEqual(profile['source_revision'], plan['revision_binding'])
        self.assertFalse(profile['old_model_body_policy_compatible'])
        folder = c.ROOT / 'inputs/dafny-vmc/overlays/pair-reference/repodisco-growth'
        self.assertIn('module RepoDiscoGrowthShift {', (folder / 'MoveToFront.dfy').read_text())
        self.assertIn('import Model = FisherYates.Model', (folder / 'MoveToFront.dfy').read_text())
        self.assertIn('import Shift = RepoDiscoGrowthShift`Public', (folder / 'PickPair.dfy').read_text())
        self.assertEqual(len(profile['source_sha256']), 93)
    def test_dafny_complete_inventory_still_requires_human_release(self):
        n, raw = dafny_raw()
        o = observe('dafny-vmc', n, raw)
        self.assertTrue(o['reference_ready_for_human_inventory_review'])
        self.assertEqual(len(o['units']), 269)
        self.assertFalse(o['controls_released'])
        self.assertFalse(o['model_scope_authorized'])

    def test_dafny_missing_provider_new_target_or_unexpected_unit_rejected(self):
        required = c.reference('dafny-vmc')['required_new_names']
        for removed, extra in [([next(iter(c.base_profile('dafny-vmc')['required_units']))], []),
                               ([required[0]], []), ([], ['New.Unplanned (correctness)'])]:
            n, raw = dafny_raw(removed=removed, extra=extra)
            self.assertFalse(observe('dafny-vmc', n, raw)['coverage_complete'])

    def test_dafny_failed_helper_cannot_hide_behind_passed_client(self):
        name = c.reference('dafny-vmc')['required_new_names'][0]
        n, raw = dafny_raw(failed=[name])
        o = observe('dafny-vmc', n, raw)
        self.assertEqual(o['category'], 'PROOF_FAILURE')
        self.assertTrue(o['coverage_complete'])
        self.assertFalse(o['proof_pass'])

    def test_warning_only_frontend_and_timeout_remain_separate(self):
        n, raw = dafny_raw()
        self.assertEqual(observe('dafny-vmc', n, raw)['category'], 'PROVED_WITH_WARNINGS')
        n['exit_code'] = 2
        raw = {'stdout.txt': b'1 parse errors detected\n', 'stderr.txt': b'', 'resources.txt': b''}
        self.assertEqual(observe('dafny-vmc', n, raw)['category'], 'PARSE_FAILURE')
        n['exit_code'] = 124
        self.assertEqual(observe('dafny-vmc', n, raw)['category'], 'TIMEOUT_OR_KILLED')









class FakeWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'outputs/real-repository-growth-001/qualification-002'
        self.root.mkdir(parents=True)
        for name in ('qualification', 'inputs'):
            shutil.copytree(c.ROOT / name, self.root / name)
        for name in ('plan.json', 'tool-image-pins.json'):
            shutil.copyfile(c.ROOT / name, self.root / name)
        # Synthetic parent bytes isolate capture/replay tests from any external source tree.
        self.original = {'Original.dfy': digest(b'synthetic fixed parent\n')}
        manifest = c.read(self.root / 'qualification/source-manifest.json')
        next(x for x in manifest if x['id'] == 'dafny-vmc')['files'] = self.original
        (self.root / 'qualification/source-manifest.json').write_text(json.dumps(manifest))
        p = self.root / 'qualification/coverage-001/profile.json'
        profile = c.read(p)
        profile['source_sha256'] = self.original
        p.write_text(json.dumps(profile))
        upstream = remote_qualification(self.root) / 'upstream/dafny-vmc'
        upstream.mkdir(parents=True)
        (upstream / 'Original.dfy').write_bytes(b'synthetic fixed parent\n')
        freeze_test_root(self.root)
        self.out = self.root / 'verification-dafny-vmc-001'
        self.out.mkdir()
        self.calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def fake_capture(self, name, args, cwd, out, env, limit):
        self.calls += 1
        self.assertEqual(limit, 300)
        d = out / name
        d.mkdir()
        native, raw = dafny_raw()
        for n in ('stdout.txt', 'stderr.txt', 'resources.txt'):
            (d / n).write_bytes(raw[n])
        csv_path = self.root / 'work/dafny-vmc' / name / 'TestResults/fake.csv'
        csv_path.parent.mkdir()
        csv_path.write_bytes(raw['csv/TestResults/fake.csv'])
        record = dict(command=args, cwd=str(cwd), exit_code=native['exit_code'], elapsed_seconds=0.01,
                      timeout=False, model_calls=0, attempts=1,
                      artifacts={n: digest(raw[n]) for n in ('stdout.txt', 'stderr.txt', 'resources.txt')})
        write(d / 'record.json', record)
        return record

    def add_review_envelope(self, row):
        env = dict(project='dafny-vmc', job_id='12345', host='fake-compute', partition='test', cpus=1,
                   execution_root=str(self.root), model_calls=0, plan_sha256=c.sha(self.root / 'plan.json'),
                   runtime_sha256=c.sha(self.root / 'runtime-freeze.json'))
        write(self.out / 'environment.json', env)
        write(self.root / 'submissions/dafny-vmc.json', dict(job_id='12345', partition='test', no_requeue=True,
              runtime_sha256=env['runtime_sha256']))
        closure = 'coverage-001/results/tool-closure.json'
        tools = dict(project='dafny-vmc', image=str(remote_qualification(self.root) / 'container-003/runtime.sif'),
                     image_sha256=c.read(self.root / 'tool-image-pins.json')['container-003']['sif_sha256'],
                     closure_path=closure, closure_manifest_sha256=c.sha(self.root / 'qualification' / closure),
                     checked_tool_files=len(c.read(self.root / 'qualification' / closure)),
                     toolchain=c.base_profile('dafny-vmc', self.root)['toolchain'])
        write(self.out / 'tools-before.json', tools)
        write(self.out / 'tools-after.json', tools)
        write(self.out / 'complete.json', dict(project='dafny-vmc', model_calls=0, native_invocations=1,
              results=[row], controls_released=False, release_requires_explicit_review=True))

    def test_fake_capture_full_replay_then_stale_raw_rejected(self):
        row = verify_one('dafny-vmc', self.out, '12345', root=self.root, native_capture=self.fake_capture)
        self.assertEqual(self.calls, 1)
        self.add_review_envelope(row)
        report = review_verification('dafny-vmc', self.root)
        self.assertEqual(report['status'], 'REFERENCE_EVIDENCE_REPLAY_PASSED')
        self.assertFalse(report['controls_released'])
        (self.out / 'pair-reference/stdout.txt').write_bytes(b'stale response')
        with self.assertRaisesRegex(ValueError, 'Raw evidence'):
            review_verification('dafny-vmc', self.root)

    def test_existing_output_prevents_second_invocation(self):
        verify_one('dafny-vmc', self.out, '12345', root=self.root, native_capture=self.fake_capture)
        with self.assertRaisesRegex(ValueError, 'no restart'):
            verify_one('dafny-vmc', self.out, '12345', root=self.root, native_capture=self.fake_capture)
        self.assertEqual(self.calls, 1)

    def test_parent_mutation_blocks_before_native_call(self):
        (remote_qualification(self.root) / 'upstream/dafny-vmc/Original.dfy').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Parent source'):
            verify_one('dafny-vmc', self.out, '12345', root=self.root, native_capture=self.fake_capture)
        self.assertEqual(self.calls, 0)
        self.assertFalse(c.read(self.out / 'parent-source-audit.json')['match'])

    def test_native_source_mutation_preserves_raw_and_rejects(self):
        def mutating(*args):
            result = self.fake_capture(*args)
            (self.root / 'work/dafny-vmc/pair-reference/Original.dfy').write_bytes(b'changed')
            return result
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            verify_one('dafny-vmc', self.out, '12345', root=self.root, native_capture=mutating)
        self.assertEqual(self.calls, 1)
        self.assertTrue((self.out / 'pair-reference/stdout.txt').exists())
        self.assertFalse(c.read(self.out / 'pair-reference/source-after.json')['match'])

    def test_frozen_overlay_change_rejected(self):
        path = self.root / 'inputs/dafny-vmc/overlays/pair-reference/repodisco-growth/PickPair.dfy'
        path.write_text(path.read_text() + '\n// changed\n')
        with self.assertRaisesRegex(ValueError, 'Pinned bytes changed'):
            c.validate_package(self.root)


if __name__ == '__main__':
    unittest.main()
