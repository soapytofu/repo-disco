import unittest,json,re
from pathlib import Path
from pilot_support import load_task,validate,make_prompt
ROOT=Path(__file__).parent
class PilotChecks(unittest.TestCase):
    def test_reference_and_negative_controls_allowed(self):
        for task in (ROOT/'tasks').iterdir():
            original=(task/'fixtures/missing/Client.dfy').read_text()
            for p in (task/'fixtures').glob('*/Client.dfy'):validate(p.read_text(),original)
    def test_assumptions_rejected(self):
        for task in (ROOT/'tasks').iterdir():
            original=(task/'fixtures/missing/Client.dfy').read_text()
            with self.assertRaises(ValueError):validate(original[:-6]+'assume false;\n'+original[-6:],original)
    def test_contracts_protected(self):
        for task in (ROOT/'tasks').iterdir():
            original=(task/'fixtures/missing/Client.dfy').read_text()
            with self.assertRaises(ValueError):validate(original.replace('ensures','requires'),original)
    def test_map_is_only_source_import_information(self):
        for task in (ROOT/'tasks').iterdir():
            sources,mapping=load_task(task)
            for name,text in sources.items():
                module=re.search(r'module\s+(\w+)',text)[1]
                self.assertEqual(mapping['imports'][module],dict(re.findall(r'import\s+(\w+)\s*=\s*(\w+)',text)))
    def test_prompt_difference_only_map(self):
        for task in (ROOT/'tasks').iterdir():
            sources,mapping=load_task(task)
            low=make_prompt('full_context',sources,mapping,'failure');high=make_prompt('with_map',sources,mapping,'failure')
            self.assertEqual(low[0],high[0])
            self.assertEqual(high[1]['content'],low[1]['content']+'\n\nStructural dependency map (duplicates source import information; no proof steps):\n'+json.dumps(mapping,sort_keys=True,indent=2))
            for text in sources.values():self.assertIn(text,low[1]['content'])
    def test_plan_balanced(self):
        plan=json.loads((ROOT/'plan.json').read_text());self.assertEqual(len(plan),12)
        for task in (ROOT/'tasks').iterdir():
            for condition in ['full_context','with_map']:
                self.assertEqual(sum(r['task']==task.name and r['condition']==condition for r in plan),2)
if __name__=='__main__':unittest.main()
