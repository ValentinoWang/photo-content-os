#!/bin/zsh
# 用 R276 的本机渲染器把一张风格库样张渲染出来，并出卡片图、小片段和检查用的联系表。
# 用法：render_sample.sh <风格 id>      （读 samples/<id>.html，12 秒 360 帧）
set -e
ID=$1
HERE=${0:A:h}
SRC=$HERE/samples/$ID.html
STUDIO=/private/tmp/claude-501/-Users-vsiyo-Desktop------photo-content-os/f43dc626-4d80-4822-a763-33a7a646fc64/scratchpad/r276/studio-107b56e
WORK=/private/tmp/claude-501/-Users-vsiyo-Desktop------photo-content-os/f43dc626-4d80-4822-a763-33a7a646fc64/scratchpad/stylelib/$ID
IMG=$HERE/../R278-direct-rescript/design/img
DIALOGUE='有个经典实验：让学生穿件尴尬的衣服走进教室。穿的人估计，约 50% 的人会注意到；实际只有约 25%。别人的注意，远比我们以为的少。'
rm -rf $WORK/in $WORK/out; mkdir -p $WORK/in
cp $SRC $WORK/in/01.html
python3 -c "import json,sys;json.dump({'shots':[{'shotId':'01','dialogue':sys.argv[1]}]},open(sys.argv[2],'w'),ensure_ascii=False)" "$DIALOGUE" $WORK/storyboard.json
echo '== 规则检查'
$STUDIO/.venv/bin/python $STUDIO/scripts/direct_video/lint.py $WORK/in --storyboard $WORK/storyboard.json || { echo '规则检查有 ERROR，先改'; exit 1; }
cat > $WORK/m.json <<J
{"width":1080,"height":1920,"fps":30,"assets_dir":"$WORK/in","fonts":[{"path":"/System/Library/Fonts/STHeiti Medium.ttc"}],"shots":[{"id":"01","html":"01.html","frames":360,"start_frame":0}],"browser_executable":"$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"}
J
echo '== 渲染（本机同一时间只跑一个浏览器：排队等前一个渲染完）'
LOCK=/private/tmp/claude-501/-Users-vsiyo-Desktop------photo-content-os/f43dc626-4d80-4822-a763-33a7a646fc64/scratchpad/stylelib/.render.lock
until mkdir $LOCK 2>/dev/null; do sleep 3; done
trap 'rmdir $LOCK 2>/dev/null' EXIT INT TERM
(cd $STUDIO && VIDEO_RENDER_PLAYWRIGHT_MODULE=$HOME/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js .venv/bin/python scripts/video_render/multi_shot.py --manifest $WORK/m.json --output $WORK/out) > $WORK/render.json 2>&1 || true
rmdir $LOCK 2>/dev/null; trap - EXIT INT TERM
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));s=d['shots'][0];print(d['status'],s.get('status'),s.get('progress_frames'),'/',s.get('total_frames'),s.get('code',''),s.get('reason',''))" $WORK/render.json || { tail -c 600 $WORK/render.json; exit 1; }
F=$WORK/out/01/frames
[ -f $F/frame-000359.png ] || { echo '没有渲染完'; exit 1; }
echo '== 卡片图、小片段、联系表'
ffmpeg -v error -y -i $F/frame-000359.png -vf scale=360:640 -q:v 3 $IMG/lib-$ID.jpg
ffmpeg -v error -y -framerate 30 -start_number 0 -i $F/frame-%06d.png -vf scale=360:640 -an -c:v libx264 -crf 28 -preset veryfast -pix_fmt yuv420p -movflags +faststart $IMG/lib-$ID.mp4
ffmpeg -v error -y -i $F/frame-000000.png -i $F/frame-000060.png -i $F/frame-000120.png -i $F/frame-000180.png -i $F/frame-000250.png -i $F/frame-000359.png \
  -filter_complex "[0]scale=270:480[a];[1]scale=270:480[b];[2]scale=270:480[c];[3]scale=270:480[d];[4]scale=270:480[e];[5]scale=270:480[f];[a][b][c][d][e][f]hstack=6" $WORK/sheet.png
cp $F/frame-000359.png $WORK/last.png
rm -rf $WORK/out   # 360 张原尺寸帧约 250 MB，本机磁盘紧，出完图就删
echo "联系表（0、2、4、6、8.3、12 秒）：$WORK/sheet.png"
echo "最后一帧原图：$WORK/last.png"
echo "卡片图：$IMG/lib-$ID.jpg  小片段：$IMG/lib-$ID.mp4"
