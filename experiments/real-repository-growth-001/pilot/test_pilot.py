"""Offline prompt and actual-parent boundary checks; no model/native calls."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import render as r
import build_freeze as build

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]

def fixtures(api):
    path=Path(api.__file__).parent/'test_fixtures.py'
    pins=r.read(path.parent/'runtime-freeze.json')['files']
    r.require(r.sha(path.read_bytes())==pins['test_fixtures.py'],'Synthetic test fixture bytes changed')
    spec=importlib.util.spec_from_file_location('growth_pilot_synthetic_fixtures',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class PromptPreparationTests(unittest.TestCase):
    def test_exact_copied_context_settings_and_templates_match_upstream_provenance(self):
        selection,views,grammar,settings=r.assets()
        for name,item in r.read(ROOT/'copy-provenance.json').items():
            source=REPO/item['source']
            self.assertEqual(source.read_bytes(),(ROOT/name).read_bytes())
            self.assertEqual(r.sha(source.read_bytes()),item['sha256'])
        self.assertEqual([len(selection['projects'][p]) for p in ('dafny-vmc','vest')],[1,16])
        self.assertEqual(settings,r.read(REPO/'experiments/real-repository-repair-pilot-001/frozen-001/settings.json'))
        self.assertFalse(settings['execution_authorized']);self.assertEqual(settings['inference_config']['maxTokens'],4096)
        self.assertTrue(all('cases/' not in e['asset'] and 'fixtures/' not in e['asset'] for values in selection['projects'].values() for e in values))
        for project,record in r.read(ROOT/'toolchain-versions.json').items():
            source=REPO/record['source_profile']
            self.assertEqual(r.sha(source.read_bytes()),record['source_profile_sha256'])
            self.assertEqual(r.read(source)['toolchain'],record['toolchain'])

    def test_display_transform_removes_only_exact_fixed_metadata_and_keeps_contracts(self):
        for sid,item in r.read(ROOT/'template-views.json')['stages'].items():
            source=(ROOT/item['asset']).read_bytes();original=bytes(source)
            view,audit=r.prompt_view(sid,source)
            removed=''.join(item['removed_prefix_lines']).encode()
            self.assertEqual(source,original);self.assertEqual(removed+view,source)
            self.assertEqual(audit['source_sha256'],item['source_sha256'])
            self.assertIn(item['begin'].encode(),view);self.assertIn(item['end'].encode(),view)
            with self.assertRaisesRegex(ValueError,'prefix'):
                r.prompt_view(sid,b'\n'+source)
            if sid=='vest-batch':self.assertIn(b'The count is supplied out of band',view)

    def test_four_stage_one_slots_are_deterministic_with_fresh_counterbalanced_lineages(self):
        order=r.order();self.assertEqual(len(order),8);seen={};payloads={}
        for entry in order:
            self.assertTrue(entry['fresh_model_context']);self.assertEqual(entry['maximum_requests'],1)
            self.assertFalse(entry['retry']);self.assertFalse(entry['blocked_slot_reassignment'])
            if entry['stage']==1:
                first=r.render_stage1(entry['slot_id']);second=r.render_stage1(entry['slot_id'])
                self.assertEqual(first,second);seen[entry['lineage_id']]=entry['slot_id']
                payloads[entry['slot_id']]=first['payload']
            else:self.assertEqual(entry['parent_slot'],seen[entry['lineage_id']])
        self.assertEqual(len(seen),4);self.assertEqual(payloads['slot-01'],payloads['slot-06'])
        self.assertEqual(payloads['slot-02'],payloads['slot-05'])
        self.assertEqual([x['project'] for x in order if x['stage']==1],['dafny-vmc','vest','vest','dafny-vmc'])

    def test_stage_two_remains_deferred_and_cannot_be_rendered_without_acceptance(self):
        for entry in r.order():
            text=r.template_text(entry['stage_id'])
            self.assertEqual(text.count(r.PARENT_TOKEN),int(entry['stage']==2))
            if entry['stage']==2:
                with self.assertRaisesRegex(ValueError,'Deferred child'):r.render_stage1(entry['slot_id'])
                with self.assertRaisesRegex(ValueError,'deferred'):r.render_stage2(entry['slot_id'])
        self.assertEqual(build.scope()['accepted_model_parent_receipts_created'],0)
        self.assertEqual(build.scope()['exact_stage_two_payloads_created'],0)
        self.assertTrue(build.scope()['budget_is_ceiling_not_target'])

    def test_rendered_instructions_preserve_language_versions_and_scope_omissions(self):
        for sid in r.TASKS:
            text=r.template_text(sid);project=r.read(ROOT/'template-views.json')['stages'][sid]['project']
            version=r.read(ROOT/'toolchain-versions.json')[project]['toolchain']
            instructions=r.grammar_text(sid)
            self.assertIn('curated context, not a complete import or dependency closure',text)
            self.assertNotIn('Analyst reference for',text);self.assertNotIn('this file is analyst-authored',text)
            self.assertNotIn('Native verification is pending',text)
            self.assertIn('16384 bytes',instructions);self.assertIn('4096 lexical tokens',instructions)
            self.assertIn('nesting depth 32',instructions)
            if project=='dafny-vmc':
                self.assertIn(version['dafny'],text);self.assertIn(version['z3'],text)
                self.assertIn('Dafny calc blocks',instructions)
            else:
                self.assertIn(version['verus'],text);self.assertIn(version['rust'],text)
                self.assertNotIn('calc',instructions)
            for forbidden in ('move-reference','move-alternative','pair-with-unproved-parent','frame-empty','batch-unproved-frame'):
                self.assertNotIn(forbidden,text)

    def test_budget_and_size_accounting_do_not_invent_child_payloads_or_token_counts(self):
        sizes=build.planned_sizes();scope=build.scope()
        self.assertEqual(scope['proposed_max_new_requests'],8);self.assertEqual(scope['maximum_output_tokens'],32768)
        self.assertFalse(scope['execution_authorized']);self.assertFalse(scope['initial_failure_feedback'])
        exact=[x for x in sizes['slots'] if x['stage']==1];deferred=[x for x in sizes['slots'] if x['stage']==2]
        self.assertEqual(len(exact),4);self.assertEqual(len(deferred),4)
        self.assertTrue(all(x['payload_bytes'] is None and x['model_input_characters'] is None for x in deferred))
        self.assertEqual(sizes['exact_stage_one_payload_bytes'],sum(len(r.encode(r.render_stage1(x['slot_id'])['payload'])) for x in exact))
        self.assertIn('not tokenization or a provider measurement',sizes['note'])


class ParentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=r.protocol_api();cls.fixture=fixtures(cls.api)

    def test_prompt_limits_match_the_actual_pinned_lexer_boundaries(self):
        lex=self.api.b.tokens;grammar=r.read(ROOT/'grammar-spec.json')
        self.assertEqual(grammar['max_body_bytes'],16384);self.assertEqual(grammar['max_lexical_tokens'],4096)
        lex('x'+' '*16383)
        with self.assertRaises(ValueError):lex('x'+' '*16384)
        self.assertEqual(len(lex('x '*4096)),4096)
        with self.assertRaises(ValueError):lex('x '*4097)
        lex('('*32+'x'+')'*32)
        with self.assertRaises(ValueError):lex('('*33+'x'+')'*33)

    def test_nonidentical_parent_body_is_preserved_and_synthetic_is_default_rejected(self):
        for project,slot in [('dafny-vmc','slot-03'),('vest','slot-04')]:
            entry=r.slot(slot);binding,artifacts,sources=self.fixture.synthetic_parent(project,chain_id=entry['lineage_id'])
            with self.assertRaises(ValueError):r.render_stage2(slot,sources,binding,artifacts)
            with self.assertRaises(ValueError):r.render_synthetic_stage2_for_tests(slot,sources,binding,artifacts)
            rendered=r.render_synthetic_stage2_for_tests(slot,sources,binding,artifacts,acknowledge_synthetic=True)
            first='vmc-move' if project=='dafny-vmc' else 'vest-frame'
            spec=r.read(ROOT/'template-views.json')['stages'][first];actual=sources[spec['path']]
            reference_case='move-reference' if project=='dafny-vmc' else 'frame-reference'
            _,_,reference,_=self.api.control_material(project,reference_case)
            self.assertNotEqual(actual,reference[spec['path']])
            view,audit=r.prompt_view(first,actual)
            text=rendered['payload']['messages'][0]['content'][0]['text']
            self.assertIn(view.decode(),text);self.assertNotIn(r.PARENT_TOKEN,text)
            self.assertEqual(rendered['rendering']['actual_parent_source_sha256'],r.sha(actual))
            self.assertEqual(rendered['rendering']['parent_view'],audit)
            self.assertTrue(rendered['rendering']['synthetic']);self.assertFalse(rendered['rendering']['eligible_as_future_dispatch_payload'])
            self.assertFalse(rendered['rendering']['execution_authorized'])

    def test_failed_parent_and_stale_or_wrong_lineage_binding_never_render_child(self):
        entry=r.slot('slot-03')
        failed,artifacts,sources=self.fixture.synthetic_parent('dafny-vmc',chain_id=entry['lineage_id'],failed=True)
        with self.assertRaises(ValueError):
            r.render_synthetic_stage2_for_tests('slot-03',sources,failed,artifacts,acknowledge_synthetic=True)
        binding,artifacts,sources=self.fixture.synthetic_parent('dafny-vmc',chain_id=entry['lineage_id'])
        for changed in (replace(binding,chain_id='vmc-lineage-02'),
                        replace(binding,native=replace(binding.native,run_id='stale-no-native-run'))):
            with self.assertRaises(ValueError):
                r.render_synthetic_stage2_for_tests('slot-03',sources,changed,artifacts,acknowledge_synthetic=True)

    def test_reference_substitution_changed_parent_and_analyst_evidence_are_rejected(self):
        entry=r.slot('slot-03');binding,artifacts,sources=self.fixture.synthetic_parent('dafny-vmc',chain_id=entry['lineage_id'])
        native,analyst,reference,_=self.api.control_material('dafny-vmc','move-reference')
        path=r.read(ROOT/'template-views.json')['stages']['vmc-move']['path']
        substituted=dict(sources);substituted[path]=reference[path]
        with self.assertRaises(ValueError):
            r.render_synthetic_stage2_for_tests('slot-03',substituted,binding,artifacts,acknowledge_synthetic=True)
        changed=dict(sources);changed[path]+=b'\n'
        with self.assertRaises(ValueError):
            r.render_synthetic_stage2_for_tests('slot-03',changed,binding,artifacts,acknowledge_synthetic=True)
        # Actual analyst evidence cannot become a model acceptance; no acceptance
        # receipt is fabricated or relabeled for this rejection check.
        with self.assertRaises(ValueError):r.render_stage2('slot-03',reference,native,analyst)

    def test_frozen_material_has_only_four_initial_payloads_and_no_acceptance(self):
        material=build.material();payloads=[name for name in material if name.endswith('.payload.json')]
        self.assertEqual(len(payloads),4);self.assertTrue(all(name.startswith('stage1/') for name in payloads))
        self.assertFalse(any('accepted.json' in name or 'stage2/' in name for name in material))
        deferred=json.loads(material['deferred-stage2.json'])
        self.assertEqual(len(deferred),4);self.assertTrue(all(x['payload'] is None for x in deferred))
        for item in deferred:self.assertFalse(item['reference_substitution']);self.assertFalse(item['synthetic_parent_eligible'])

if __name__=='__main__':unittest.main()
