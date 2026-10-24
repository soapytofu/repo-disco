"""Offline frozen-request and response-evaluation CLI. No API transport."""
import argparse,hashlib,json
from pathlib import Path
from harness import ROOT,request_for,evaluate

def verify_freeze():
    for name,expected in json.loads((ROOT/'frozen-bundle.json').read_text()).items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen artifact changed: '+name)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='operation',required=True)
    sub.add_parser('check')
    req=sub.add_parser('request');req.add_argument('sequence',type=int)
    ev=sub.add_parser('evaluate');ev.add_argument('condition',choices=['shared','separate']);ev.add_argument('response',type=Path);ev.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();verify_freeze()
    if args.operation=='check':print('Frozen bundle intact; authorized model calls: 0')
    elif args.operation=='request':
        trial,messages=request_for(args.sequence);print(json.dumps(dict(trial=trial,messages=messages),indent=2))
    else:print(json.dumps(evaluate(args.condition,args.response.read_text(),args.output),indent=2))
if __name__=='__main__':main()
