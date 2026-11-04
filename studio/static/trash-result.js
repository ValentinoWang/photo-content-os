export function reconcileTrashResult(candidates, selected, response) {
  const selection = new Set(selected);
  const receipts = Array.isArray(response.receipts) ? response.receipts : [];
  const pending = Array.isArray(response.pending) ? response.pending : [];
  const moved = new Set(receipts.filter(item => item.status === 'trashed' && selection.has(item.candidate_number))
    .map(item => item.candidate_number));
  const remaining = selected.filter(number => !moved.has(number));
  const failed = response.status !== 'completed' || !Array.isArray(response.pending) || pending.length > 0 || remaining.length > 0;
  const codes = [...new Set(pending.map(item => item.failure_code || '未知'))];
  const uncertain = codes.includes('post_move_verification_failed');
  const message = failed
    ? `已移入 ${moved.size} 项，${remaining.length} 项${uncertain ? '状态待确认' : '没移走'}（错误码 ${codes.join('、') || '未知'}）。`
    : `已移入系统回收站：${moved.size} 项。`;
  return {
    candidates: candidates.filter(candidate => !moved.has(candidate.candidate_number)),
    selected: remaining,
    message,
    failed,
  };
}
