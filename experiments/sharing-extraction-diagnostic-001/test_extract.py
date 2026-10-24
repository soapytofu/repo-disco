import json,unittest
from extract import extract
class ExtractionTests(unittest.TestCase):
    def test_prose_removed_without_changing_json(self):
        obj=json.dumps({'ClientA.dfy':'source { }','ClientB.dfy':'other'})
        text='Explanation with {invalid} prefix\n'+obj+'\n'
        start,end,value=extract(text)
        self.assertEqual(text[start:end],obj)
        self.assertEqual(value,json.loads(obj))
    def test_ambiguous_or_incomplete_objects_rejected(self):
        obj=json.dumps({'ClientA.dfy':'a','ClientB.dfy':'b'})
        for text in [obj+'\n'+obj,obj+' explanation','{"ClientA.dfy":"a"}','{"ClientA.dfy":"a","ClientA.dfy":"x","ClientB.dfy":"b"}']:
            with self.subTest(text=text),self.assertRaises(ValueError):extract(text)
if __name__=='__main__':unittest.main()
