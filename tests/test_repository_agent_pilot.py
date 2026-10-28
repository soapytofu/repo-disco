import json
from types import SimpleNamespace
import unittest
from repository_agent_pilot import EXP,ORDER,files_at,task_parts,AgentGate
from language.dafny.candidate import prepare_candidate,hashes

class PilotTests(unittest.TestCase):
    def test_all_reference_responses_parse_and_guard_exactly(self):
        for family,condition in ORDER:
            with self.subTest(family=family,condition=condition):
                base=files_at(EXP/'fixtures'/family/(condition+'_empty'))
                positive=files_at(EXP/'fixtures'/family/(condition+'_reference'))
                manifest,decode,guards=task_parts(family,condition,base)
                raw={'text':json.dumps({k:positive[k].decode() for k in manifest['editable']})}
                changes=decode(raw,SimpleNamespace(files=base))
                candidate=prepare_candidate(base,changes,entry=manifest['entry'],expected_hashes=hashes(base),guards=guards)
                self.assertEqual(dict(candidate.files),positive)
                self.assertIn('output_protocol',manifest)
    def test_exact_final_chat_messages_enter_request_gate(self):
        seen=[]
        class Recorder:
            def invoke(self,messages,**identity):seen.append((messages,identity));return {'text':'response'}
        context={'manifest':{'output_protocol':'frozen'},'feedback':{'stdout':'error'},'files':{'A.dfy':'source'}}
        answer=AgentGate(Recorder()).invoke(context,task_id='a',attempt_id='b')
        self.assertEqual(json.loads(seen[0][0][1]['content']),context)
        self.assertEqual(seen[0][1],{'task_id':'a','attempt_id':'b'})
        self.assertEqual(answer,{'text':'response'})
    def test_contract_tampering_rejected_for_all_cases(self):
        for family,condition in ORDER:
            base=files_at(EXP/'fixtures'/family/(condition+'_empty'))
            positive=files_at(EXP/'fixtures'/family/(condition+'_reference'))
            manifest,decode,guards=task_parts(family,condition,base)
            raw={k:positive[k].decode() for k in manifest['editable']}
            raw[manifest['editable'][0]]=raw[manifest['editable'][0]].replace('ensures ','ensures false && ',1)
            with self.assertRaises(ValueError):decode({'text':json.dumps(raw)},SimpleNamespace(files=base))

if __name__=='__main__':unittest.main()
