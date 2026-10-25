"""Studio-owned visual examples, submitted issues and adopted user rules."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import shutil
import uuid

from direct_video.media import atomic_bytes

CATEGORIES = {'main': '主次不清', 'dim': '主次不清', 'del': '字太多', 'short': '字太多',
              'space': '太空或挤在上面', 'color': '颜色乱', 'sync': '跟口播对不上'}


def read_json(path: Path, default):
    # Missing and unreadable are deliberately different outcomes.
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return copy.deepcopy(default)


def write_json(path: Path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode())


class RevisionLibrary:
    """All methods are called under the owning Generator's lock."""
    def __init__(self, state_dir):
        self.root = state_dir

    def samples(self):
        return read_json(self.root / 'direct-samples' / 'index.json', [])

    def sample(self, job, shot, root, enabled, title, timestamp):
        rows = self.samples()
        identity = (job['projectId'], job['jobId'], shot['shotId'], shot['currentVersion'])
        matches = lambda row: tuple(row[k] for k in ('projectId', 'jobId', 'shotId', 'version')) == identity
        existing = next((row for row in rows if matches(row)), None)
        if enabled and existing is None:
            sid = 'sample_' + uuid.uuid4().hex[:24]
            destination = self.root / 'direct-samples' / sid
            destination.mkdir(parents=True)
            try:
                shutil.copyfile(root / 'shots' / (shot['shotId'] + '.html'), destination / 'code.html')
                shutil.copyfile(root / 'posters' / (shot['shotId'] + '.jpg'), destination / 'poster.jpg')
                rows.append(dict(zip(('projectId', 'jobId', 'shotId', 'version'), identity),
                                 sampleId=sid, projectTitle=title, savedAt=timestamp,
                                 dialogue=shot['dialogue'], mainAction=shot['mainAction']))
                write_json(self.root / 'direct-samples' / 'index.json', rows)
            except Exception:
                shutil.rmtree(destination)
                raise
        elif not enabled and existing:
            write_json(self.root / 'direct-samples' / 'index.json', [row for row in rows if not matches(row)])
            shutil.rmtree(self.root / 'direct-samples' / existing['sampleId'])

    def is_sample(self, job, shot):
        return any((row['projectId'], row['jobId'], row['shotId'], row['version']) ==
                   (job['projectId'], job['jobId'], shot['shotId'], shot.get('currentVersion')) for row in self.samples())

    def closest(self, shot):
        def bigrams(text):
            return set(zip(text, text[1:]))
        target = bigrams(shot['dialogue'] + (shot['mainAction'] or ''))
        def similarity(row):
            other = bigrams(row['dialogue'] + (row['mainAction'] or ''))
            return len(target & other) / max(1, len(target | other))
        rows = sorted(self.samples(), key=lambda row: (-similarity(row), row['sampleId']))[:2]
        return [{**row, 'code': (self.root / 'direct-samples' / row['sampleId'] / 'code.html').read_text()} for row in rows]

    def rules_state(self):
        return read_json(self.root / 'direct-rules' / 'state.json',
                         {'revision': 0, 'rules': [], 'proposals': [], 'issues': []})

    def save_rules(self, value):
        write_json(self.root / 'direct-rules' / 'state.json', value)

    def rules(self, base):
        state = self.rules_state()
        return base.read_text() + '\n\n用户画面规则（第 %d 版）\n' % state['revision'] + '\n'.join(state['rules'])

    def record(self, job, shot, lines, title, timestamp):
        state = self.rules_state()
        for line in lines:
            if line.get('own'):
                continue
            category = CATEGORIES[line.get('action', line.get('issue'))]
            state['issues'].append({'category': category, 'text': line['text'], 'projectId': job['projectId'],
                                    'projectTitle': title, 'jobId': job['jobId'], 'shotId': shot['shotId'],
                                    'submittedAt': timestamp})
        self.save_rules(state)

    def draft_candidates(self):
        state = self.rules_state()
        candidates = []
        for category in dict.fromkeys(CATEGORIES.values()):
            issues = [row for row in state['issues'] if row['category'] == category]
            covered = max((p['throughCount'] for p in state['proposals'] if p['category'] == category), default=0)
            if len(issues) >= 3 and len(issues) - covered >= 3:
                proposal = {'proposalId': 'proposal_' + uuid.uuid4().hex[:24], 'category': category,
                            'throughCount': len(issues), 'status': 'running', 'text': None, 'failureCode': None}
                state['proposals'].append(proposal)
                candidates.append((copy.deepcopy(proposal), [row['text'] for row in issues]))
        self.save_rules(state)
        return candidates

    def finish_draft(self, proposal_id, text):
        state = self.rules_state()
        proposal = next(p for p in state['proposals'] if p['proposalId'] == proposal_id)
        proposal.update(status='pending' if text else 'failed', text=text, failureCode=None if text else 'model_failed')
        self.save_rules(state)

    def decide(self, proposal_id, adopt):
        from direct_video.generate import DirectVideoError
        state = self.rules_state()
        proposal = next((p for p in state['proposals'] if p['proposalId'] == proposal_id), None)
        if proposal is None:
            raise DirectVideoError('proposal_not_found')
        desired = 'adopted' if adopt else 'rejected'
        if proposal['status'] == desired:
            return proposal
        if proposal['status'] != 'pending':
            raise DirectVideoError('proposal_not_ready')
        proposal['status'] = desired
        if adopt:
            state['revision'] += 1
            state['rules'].append(proposal['text'])
        self.save_rules(state)
        return proposal

    def log(self):
        state = self.rules_state()
        return {'rulesRevision': state['revision'], 'categories': [
            {'category': category, 'count': sum(row['category'] == category for row in state['issues']),
             'sources': [row for row in state['issues'] if row['category'] == category],
             'proposals': [row for row in state['proposals'] if row['category'] == category]}
            for category in dict.fromkeys(CATEGORIES.values())]}

    def poster(self, sample_id):
        from direct_video.generate import DirectVideoError
        if not re.fullmatch(r'sample_[a-f0-9]{24}', sample_id) or not any(row['sampleId'] == sample_id for row in self.samples()):
            raise DirectVideoError('sample_not_found')
        path = self.root / 'direct-samples' / sample_id / 'poster.jpg'
        if not path.is_file():
            raise DirectVideoError('artifact_not_found')
        return path
