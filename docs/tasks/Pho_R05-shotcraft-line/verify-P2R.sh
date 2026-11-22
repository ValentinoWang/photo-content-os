#!/bin/bash
cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry || exit 1
S=scripts/direct_video/recipe_samples; bad=0
for id in blur-slide marker-underline-title gauge-readout-moves beat-cut-moves product-card-progressive-assemble list-reveal circle-match-iris spotlight-hero-card; do for o in portrait landscape; do
  f=$S/$id/$o.html; test -f $f || { echo "MISSING $f"; bad=1; continue; }
  grep -q -- '--ink:#121317' $f && grep -q -- '--accent:#ff5b2e' $f && grep -q '制作台' $f || { echo "NO SYSTEM $f"; bad=1; }
  grep -qE '示意|一段新的开始|让想法|让每个想法|年度亮点|随行收纳盒|一目了然' $f && { echo "FILLER $f"; bad=1; }
  out=$(bash /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/docs/tasks/Pho_R05-shotcraft-line/lint-one.sh $f 2>&1); echo "$out" | grep -q '"errors": \[\]' || { echo "LINT $f: $out"; bad=1; }
  for x in jpg mp4; do test $S/$id/$o.$x -nt $f || { echo "STALE $id/$o.$x"; bad=1; }; done
  test -s $HOME/.photo-content-os/evidence/Pho_R05-shotcraft-line/work/$id-$o/sheet.png || { echo "NO SHEET $id-$o"; bad=1; }
done; done
[ $bad = 0 ] && echo "ok 16 samples restyled"; exit $bad
