#!/usr/bin/env python3
"""Generate approved taxonomy text from its authority, without copied labels."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_music_analysis_registry import display_copy

def approved_copy():
    registry=json.loads((ROOT/'music-analysis.registry.json').read_text())
    contract=json.loads((ROOT/'docs/tasks/R223-music-beat-map/mock/design-contract.json').read_text())
    task=(ROOT/'docs/tasks/R223-music-beat-map/TASK.md').read_text()
    # B1 explicitly approves immediate analysis feedback, including tags-only retries.
    progress=task.split('点下去立刻把这首改成「',1)[1].split('」',1)[0]
    return {'copy':{state:list(dict.fromkeys(display_copy(registry)+[progress])) for state in contract['states']},
            'sources':['music-analysis.registry.json','docs/tasks/R223-music-beat-map/TASK.md#B1']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.write_text(json.dumps(approved_copy(),ensure_ascii=False,indent=2)+'\n')
    print('Approved taxonomy and TASK B1 immediate progress copy generated')
if __name__=='__main__':main()
