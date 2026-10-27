#!/usr/bin/env bash
# 在开发机上执行：公网暴露检查（10-26 事故：cloudflared 临时隧道把以 /root/Cadenvo 为根的 http.server 挂到公网，.env、secrets 返回 200）。
# 隧道一律列出；对外的文件服务，根目录下（3 层内）有 .env、secrets/、*.pem、id_rsa 就报红，退出 1。只报不停（停要先问，正在泄露时可先停隧道止血）。
found=0
t=$(ps -eo pid=,etimes=,args= | grep -E 'cloudflared|ngrok|frpc|localtunnel|[[:space:]]bore[[:space:]]' | grep -vE 'grep|exposure_check')
[ -n "$t" ] && { echo "公网隧道："; echo "$t" | awk '{printf "  pid %s 已跑 %d 分钟：", $1, $2/60; $1=$2=""; print substr($0,1,140)}'; }
while read -r pid; do
  # 只认真正的服务进程（python、node、caddy）；命令行里带 http.server 字样的 bash 外壳不算（10-26 误报过）
  grep -qE '^(python[0-9.]*|node|caddy)$' /proc/$pid/comm 2>/dev/null || continue
  a=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
  d=$(sed -nE 's/.*--directory[= ]+([^ ]+).*/\1/p' <<<"$a")
  [[ $a == *review_server.py* ]] && d=$(awk '{print $NF}' <<<"$a")     # rbox publish 的只读服务：根目录是最后一个参数
  [ -n "$d" ] || d=$(readlink /proc/$pid/cwd 2>/dev/null)
  [ -n "$d" ] || continue
  bad=$(find "$d" -maxdepth 3 \( -name .env -o -name secrets -o -name '*.pem' -o -name id_rsa -o -name auth.json \) 2>/dev/null | head -3 | tr '\n' ' ')
  [ -n "$bad" ] && { echo "红：pid $pid 的文件服务根目录 $d 下有 ${bad}（经隧道就是公网可读）"; found=1; }
done < <(pgrep -f 'http\.server|SimpleHTTPServer|http-server|serve -s|npx serve|caddy file-server|review_server\.py' 2>/dev/null)
[ -z "$t" ] && [ "$found" = 0 ] && echo "无公网隧道，文件服务根目录下无密钥"
[ "$found" = 0 ] || exit 1
