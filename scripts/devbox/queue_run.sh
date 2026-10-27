#!/usr/bin/env bash
# 原版取自 Cadenvo wsy@6cc3e74d；寸木 agent-85 加 light 队（10-26，和 cadenvo-31 对齐过设计），Cadenvo 照原样搬回。
# 从 10-27 起两边不再一样：Cadenvo 停在 be326fbb9（light 最多 3 个并排），没有 backend 队和 baseline- 任务；以后要用就整份照搬（cadenvo-f6，wsy@da890536）。
# rbox bg 的排队外壳（开发机上跑）：按队名排队，排了多久写进任务日志和 queue.tsv（时间、队、任务、等了几秒、light 的槽位）。
# 用法：queue_run.sh <队名> <任务名> <任务脚本>。由 `RBOX_QUEUE=<队名> rbox bg …` 调用，不直接用。
# 队名：
#   heavy[-组]  全量门禁、计时类：和同组的 heavy、light 都互斥，同一时间只跑一个
#   light[-组]  只用一两个核的任务（单个浏览器、单进程 pytest）：同组 light 之间最多 3 个并排，和同组 heavy 互斥
#               （10-27 02:14 两个 light 在跑时开发机 CPU 空闲 81%，R289 的单浏览器探查排在 20–30 分钟的 pytest 后面，从 2 加到 3）
#   backend[-组] 单进程后端 pytest：最多 2 个并排，不碰 heavy、light 的锁，也不过旋转门（不看时间、不开浏览器，叠着跑没关系）。
#               10-27 02:36：单进程 pytest 放在 light 里，一个跑了 24 分钟的 pytest 握着共享锁，heavy 在等就把旋转门关了，
#               后面 11 个任务全堵住，开发机 CPU 空闲 85%。长任务不能进 light
#   其他        各自一把独立的排他锁。比如 Cadenvo 的 short：不怕挤、5 分钟内的短任务，和 heavy 并行
# 组后缀让自测用自己的锁，不碰真实的队（heavy-selftest123 和 light-selftest123 是一组）。
# 防饿死：heavy 等主锁期间握着旋转门，light 要先过旋转门再拿共享锁，所以有 heavy 在等时，新来的 light 进不去。
# 反过来，连续来的 heavy 会让 light 一直等：heavy 本来就该先跑（和 cadenvo-31 对齐，10-26）。
# 10-26 晚：几条线各写各的「负载低于 4/6 才开跑」循环，阈值不一，负载一降就一起冲进去，门槛高的那条可能一直排不上；
# 排队上线后寸木 heavy 队从 19:55 起没空过，单浏览器的轻任务也得一个一个等全量跑完（最长 883 秒），所以加了 light。
q=$1 name=$2 job=$3 L=$(dirname "$3") slot=""
t0=$(date +%s); echo "[rbox] 排队 ${q}：$(date '+%H:%M:%S') 开始等"
case "$q" in
  heavy|heavy-*)
    g=${q#heavy}
    exec 8>"$L/queue-turnstile$g.lock"; flock 8   # 握住旋转门：之后来的 light 卡在门外
    exec 9>"$L/queue-heavy$g.lock"; flock -x 9    # 等已经进去的 light、heavy 跑完。锁名和只有 heavy 的旧版一样，换版时还在旧版里排队的任务也互斥
    exec 8>&-                                      # 轮到了就放开旋转门
    # 共享基线（任务名 baseline-…）要在干净的机器上跑：拿到主锁以后再把 backend 的两个槽位也占住，等在跑的后端测试结束，跑的期间不让新的进来。
    # 10-27 02:58 baseline-f97fe4f6d-qa 和一个后端 pytest 叠着跑，负载 13；基线多出的假红会把候选同一步的真红算成「基线本来就红」。
    # - 两个槽位轮流试、空出来一个就先占住一个：按顺序死等第 1 个的话，等的期间第 2 个空着，新来的后端测试照样溜进去。
    # - 等槽位期间握着 backend 的旋转门：在跑的后端测试一结束，空出来的槽位归基线，新来的不能抢先（10-27 04:40 自测抓到被插队）。
    # - 等有上限（默认 600 秒，RBOX_BASELINE_QUIET_MAX 可改）：到点就带着已占的槽位开跑，日志写「不干净」，收基线时记进备注。
    #   旁边多一个后端测试，两边都没改过的步骤用时中位数只慢 8%；偶发的计时红由 baseline compare 的「不稳定」兜住。
    # - 先拿主锁、后占槽位：等主锁时不占槽位，后端测试照常跑；占槽位时握着主锁，light 最多被多挡一个上限。
    #   顺序改过两次：03:36 先主锁后槽位、没有上限，a437 的基线 qa 握着主锁等一个 80 分钟的后端全量，light 全堵；
    #   改成先槽位后主锁以后，05:34 a30fbd0b3 的基线 qa 占着两个槽位等 r289-final2 的主锁 39 分钟，三个后端测试各等了约 30 分钟。
    #   有了上限，先主锁这边的代价有界（≤600 秒），先槽位那边的代价随前面 heavy 的长短无界，所以回到先主锁
    # 并行模式（RBOX_BASELINE_PARALLEL=1）不碰后端槽位：10-27 08:55 baseline-785d15aae-qa 按上限 0 顺手占了一个空槽位，
    # 另一个被别的任务占着，同一提交的后端那一半反而没槽位可用
    case "${RBOX_BASELINE_PARALLEL:-}:$name" in 1:baseline-*)
      echo "[rbox] 不干净：并行模式，不占后端槽位，和后端测试一起跑" ;; *:baseline-*)
      exec 4>"$L/queue-backend-turnstile$g.lock"; flock 4
      exec 5>"$L/queue-backend$g-1.lock" 6>"$L/queue-backend$g-2.lock"; h5="" h6=""; qmax=${RBOX_BASELINE_QUIET_MAX:-600}; qt0=$(date +%s)
      until [ -n "$h5" ] && [ -n "$h6" ]; do
        [ -n "$h5" ] || { flock -n 5 && h5=1; }; [ -n "$h6" ] || { flock -n 6 && h6=1; }
        { [ -n "$h5" ] && [ -n "$h6" ]; } && break
        if [ $(( $(date +%s) - qt0 )) -ge "$qmax" ]; then
          echo "[rbox] 不干净：等在跑的后端测试超过 ${qmax} 秒，和它一起跑（占着空出来的槽位，不再放新的进来）"; break; fi
        sleep 2
      done
      exec 4>&- ;;
    esac ;;
  light|light-*)
    g=${q#light}
    exec 8>"$L/queue-turnstile$g.lock"; flock 8; exec 8>&-   # 过一下旋转门：有 heavy 在等就卡在这里
    exec 9>"$L/queue-heavy$g.lock"; flock -s 9                # 和别的 light 共享，和 heavy 互斥
    while [ -z "$slot" ]; do
      for i in 1 2 3; do exec 7>"$L/queue-light$g-$i.lock"; if flock -n 7; then slot=$i; break; fi; exec 7>&-; done
      [ -n "$slot" ] || sleep 2
    done ;;
  backend|backend-*)
    g=${q#backend}
    # 共享基线的后端那一半（baseline-<提交>-backend）等同一提交的 qa（baseline-<提交>-qa，tmux 会话同名）先跑完再抢槽位：
    # 不然在跑的后端测试一结束，它和 qa 抢同一个空槽位，抢到了 qa 就得再等它 20 多分钟，这期间别的后端测试也进不来。
    # 10-27 03:52 有一条线为此手写了「Deferred: shared baseline QA must finish」的外壳；等的时候什么锁都不握
    # RBOX_BASELINE_PARALLEL=1：赶时间时两半一起跑，不等 qa（10-27 08:12 开发机 10:20 到期，先后跑要到 10:00）
    case "${RBOX_BASELINE_PARALLEL:-}:$name" in 1:*) ;; *:baseline-*-backend)
      sib=${name%-backend}-qa
      tmux has-session -t "=$sib" 2>/dev/null && echo "[rbox] 先等同一提交的 ${sib} 跑完"
      while tmux has-session -t "=$sib" 2>/dev/null; do sleep 5; done ;;
    esac
    exec 4>"$L/queue-backend-turnstile$g.lock"; flock 4; exec 4>&-   # 过一下 backend 的旋转门：有基线在等槽位就让它先拿
    while [ -z "$slot" ]; do
      for i in 1 2; do exec 7>"$L/queue-backend$g-$i.lock"; if flock -n 7; then slot=$i; break; fi; exec 7>&-; done
      [ -n "$slot" ] || sleep 2
    done ;;
  *)
    exec 9>"$L/queue-$q.lock"; flock 9 ;;
esac
w=$(( $(date +%s) - t0 )); echo "[rbox] 轮到了，排了 ${w} 秒${slot:+（槽位 ${slot}）}"
printf '%s\t%s\t%s\t%s\t%s\n' "$(date '+%m-%d %H:%M')" "$q" "$name" "$w" "${slot:--}" >> "$L/queue.tsv"
bash "$job" 4>&- 5>&- 6>&- 7>&- 8>&- 9>&-   # 任务不继承锁：任务里留下的后台进程不会一直占着队；本外壳等任务结束才退出、放锁
