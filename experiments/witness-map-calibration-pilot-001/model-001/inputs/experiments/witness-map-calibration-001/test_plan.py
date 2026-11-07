import copy,json,tempfile,unittest
from pathlib import Path
import prepare
HERE=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_exact_rebuild(self):
  prepare.validate()
 def test_trial_balance_and_no_budget_inference(self):
  plan=prepare.load(HERE/'plan.json');tasks=prepare.load(prepare.TASK/'tasks.json');prepare.validate_plan(plan,tasks)
  for key,value in [('execution_authorized',True),('proposed_calls',17),('sdk_total_max_attempts',2),('feedback',True),('reassign_unused',True),('slurm_requeue',True)]:
   bad=copy.deepcopy(plan);bad[key]=value
   with self.assertRaises(ValueError):prepare.validate_plan(bad,tasks)
 def test_missing_duplicate_and_order_rejected(self):
  plan=prepare.load(HERE/'plan.json');tasks=prepare.load(prepare.TASK/'tasks.json')
  for mutation in ['duplicate','position','size']:
   bad=copy.deepcopy(plan)
   if mutation=='duplicate':bad['blocks'][0][0]=bad['blocks'][0][1]
   elif mutation=='position':bad['blocks'][1][0],bad['blocks'][1][1]=bad['blocks'][1][1],bad['blocks'][1][0]
   else:bad['blocks'][0].pop()
   with self.assertRaises(ValueError):prepare.validate_plan(bad,tasks)
 def test_requests_only_contain_declared_empty_context(self):
  plan=prepare.load(HERE/'plan.json');guard=prepare.common['guard'](prepare.TASK/'protocol/body_guard.py')
  for t in prepare.load(prepare.TASK/'tasks.json'):
   seeds=prepare.common['files'](prepare.TASK/'fixtures'/t['task_id']/'empty');request=prepare.load(HERE/'frozen-001/requests'/(t['task_id']+'.json'))
   self.assertEqual(set(request),{'modelId','system','messages','inferenceConfig'});self.assertEqual(len(request['messages']),1)
   self.assertEqual(request['messages'][0]['content'],[{'text':prepare.prompt(t,seeds,guard.policy(t))}])
   self.assertEqual(request['inferenceConfig'],plan['inference_config'])
   for n in t['editable_files']:guard.split_seed(seeds[n])
   self.assertNotIn('Prove(...) denotes self-recursion',(HERE/'syntax.txt').read_text())
 def test_each_repeated_sample_uses_identical_request(self):
  slots=prepare.load(HERE/'frozen-001/trials.json');self.assertEqual(len({s['trial_id'] for s in slots}),16)
  grouped={}
  for s in slots:grouped.setdefault(s['task_id'],set()).add(s['request_sha256']);self.assertEqual(s['request_sha256'],prepare.sha(HERE/'frozen-001'/s['request_path']))
  self.assertEqual(len(grouped),8);self.assertTrue(all(len(v)==1 for v in grouped.values()))
if __name__=='__main__':unittest.main(verbosity=2)
