import assert from 'node:assert/strict';
import {reconcileTrashResult} from '../studio/static/trash-result.js';

const candidates = ['a', 'b', 'c'].map(candidate_number => ({candidate_number}));
const selected = ['a', 'b'];
const receipt = candidate_number => ({candidate_number, status: 'trashed'});

const success = reconcileTrashResult(candidates, selected, {
  status: 'completed', receipts: [receipt('a'), receipt('b')], pending: [],
});
assert.deepEqual(success.candidates.map(c => c.candidate_number), ['c']);
assert.deepEqual(success.selected, []);
assert.equal(success.message, '已移入系统回收站：2 项。');
assert.equal(success.failed, false);

const partial = reconcileTrashResult(candidates, selected, {
  status: 'partial', receipts: [receipt('a')], pending: [{candidate_number: 'b', failure_code: 'system_trash_failed'}],
});
assert.deepEqual(partial.candidates.map(c => c.candidate_number), ['b', 'c']);
assert.deepEqual(partial.selected, ['b']);
assert.equal(partial.message, '已移入 1 项，1 项没移走（错误码 system_trash_failed）。');
assert.equal(partial.failed, true);

const unknown = reconcileTrashResult(candidates, selected, {
  status: 'partial', receipts: [], pending: [
    {candidate_number: 'a', failure_code: 'future_failure_42'},
    {candidate_number: 'b', failure_code: 'other_failure'},
  ],
});
assert.deepEqual(unknown.candidates, candidates);
assert.deepEqual(unknown.selected, selected);
assert.match(unknown.message, /future_failure_42/);
assert.match(unknown.message, /other_failure/);
assert.equal(unknown.failed, true);

const uncertain = reconcileTrashResult(candidates, selected, {
  status: 'partial', receipts: [receipt('a')], pending: [{candidate_number: 'b', failure_code: 'post_move_verification_failed'}],
});
assert.deepEqual(uncertain.candidates.map(c => c.candidate_number), ['b', 'c']);
assert.match(uncertain.message, /1 项状态待确认/);
assert.doesNotMatch(uncertain.message, /没移走/);

const missing = reconcileTrashResult(candidates, selected, {status: 'partial', receipts: [], pending: []});
assert.deepEqual(missing.candidates, candidates);
assert.deepEqual(missing.selected, selected);
assert.equal(missing.failed, true);
const inconsistent = reconcileTrashResult(candidates, selected, {
  status: 'completed', receipts: [receipt('a'), receipt('a'), receipt('outside')], pending: [],
});
assert.deepEqual(inconsistent.candidates.map(c => c.candidate_number), ['b', 'c']);
assert.deepEqual(inconsistent.selected, ['b']);
assert.equal(inconsistent.failed, true);
console.log('trash result reconciliation: complete, partial, unknown codes, and missing receipts');
