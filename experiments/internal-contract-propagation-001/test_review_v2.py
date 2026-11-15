"""Synthetic scope tests for the exact Endpoint logger exception; no tools."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import review_v2 as v
import test_review as original_tests


class NarrowLoggerScope(unittest.TestCase):
    def prepare(self,task_id):
        adapter=v.Adapter();old=adapter.old
        case=next(c for c in old.load(v.ROOT/'cases.json') if c['task_id']==task_id and c['variant']=='reference')
        task=next(t for t in old.load(v.ROOT/'tasks.json') if t['task_id']==task_id)
        files=original_tests.source(case)
        declarations=adapter.source_scope(files,task,case,files)
        return adapter,declarations,files,task,case

    def test_exact_endpoint_absence_is_unlogged_and_does_not_invent_a_pass(self):
        adapter,decls,*_=self.prepare('capped_endpoint_return_migration')
        synthetic=original_tests.csv_text({n:k for n,k in decls.items() if n!='Kernel.Endpoint'},['Client.Target'])
        with self.assertRaisesRegex(ValueError,'Missing declaration'):adapter.old_named_units({'synthetic.csv':synthetic},decls)
        result=adapter.named_units({'synthetic.csv':synthetic},decls)
        self.assertEqual(result['local_targets'],{'Client.Target':False,'Helper.Transfer':True})
        self.assertEqual(result['logged_provider_units'],[])
        self.assertEqual(result['unlogged_definitions'],[dict(symbol='Kernel.Endpoint',source_file='Kernel.dfy',
            source_sha256='4508c49460dcd0b728d9438545a35e3f772bf0409622b34154d06af940f0c4be',
            classification='unlogged_definition_not_verified_provider_unit')])
        self.assertNotIn('Kernel.Endpoint',str(result['units']))

    def test_all_three_map_providers_and_both_methods_remain_mandatory(self):
        for task_id in ('capped_endpoint_return_migration','extracted_entry_return_migration'):
            adapter,decls,*_=self.prepare(task_id)
            for missing in decls:
                if missing=='Kernel.Endpoint':continue
                smaller={n:k for n,k in decls.items() if n!=missing and n!='Kernel.Endpoint'}
                with self.subTest(task_id=task_id,missing=missing):
                    with self.assertRaises(ValueError):adapter.named_units({'synthetic.csv':original_tests.csv_text(smaller)},decls)

    def test_unexpected_unlogged_declaration_or_source_hash_is_rejected(self):
        adapter,decls,files,task,case=self.prepare('capped_endpoint_return_migration')
        with self.assertRaisesRegex(ValueError,'source context'):
            adapter.named_units({'synthetic.csv':original_tests.csv_text(decls)},dict(decls,**{'Kernel.Unlisted':'function'}))
        adapter.scope['unlogged_definitions'][0]['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'source hash'):
            adapter.source_scope(files,task,case,files)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'changed-scope.json';scope=v.load_scope()
            scope['unlogged_definitions'].append(dict(scope['unlogged_definitions'][0],symbol='Kernel.Extra'))
            path.write_text(json.dumps(scope))
            with self.assertRaisesRegex(ValueError,'scope changed'):v.load_scope(path)

    def test_observed_endpoint_failure_cannot_use_absence_exception(self):
        adapter,decls,*_=self.prepare('capped_endpoint_return_migration')
        result=adapter.named_units({'synthetic.csv':original_tests.csv_text(decls,['Kernel.Endpoint'])},decls)
        self.assertEqual(result['unlogged_definitions'],[])
        self.assertFalse(result['providers_verified'])
        self.assertEqual(result['unverified_providers'],['Kernel.Endpoint (well-formedness)'])

    def test_duplicate_or_malformed_evidence_still_rejected(self):
        adapter,decls,*_=self.prepare('capped_endpoint_return_migration')
        methods={n:k for n,k in decls.items() if n!='Kernel.Endpoint'}
        text=original_tests.csv_text(methods)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            adapter.named_units({'one.csv':text,'two.csv':text},decls)
        with self.assertRaises(ValueError):adapter.named_units({'synthetic.csv':text.replace('Passed','Unknown',1)},decls)

    def test_complete_synthetic_archive_keeps_original_all_logged_interpretation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'verification';out.mkdir();original_tests.make_archive(out)
            # Source snapshot is the archived pinned input subset; it carries
            # no unrelated actual submission metadata into this synthetic test.
            result,_=v.Adapter().audit(out,out)
            self.assertTrue(result['all_expected'])
            self.assertEqual(result['counts'],{'success':6,'proof_failure':12})
            self.assertEqual(result['unlogged_definition_observations'],0)
            for row in result['checks']:
                named=row['named_evidence']
                self.assertNotIn('providers_verified',named)
                self.assertTrue(named['logged_provider_units_verified'])
                self.assertTrue(named['provider_observation_complete'])


if __name__=='__main__':unittest.main(verbosity=2)
