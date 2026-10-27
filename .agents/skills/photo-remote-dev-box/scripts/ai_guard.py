"""开发机不跑 AI（用户 2026-10-26）：判断一条要交给开发机执行的命令是否在调用 Claude、Codex 或搬运凭据。
用法：python3 -I ai_guard.py <argv...>；退出 0 放行，1 = 调用 AI 程序（RBOX_ALLOW_AI_WORDS=1 可放行），2 = 凭据（永不放行）。
按命令拆段，只看每段真正执行的程序名，不对整串文字跑正则，避免误伤 docs/codex-notes、grep codex 这类普通用法（与寸木 agent-6a 商定）。"""
import os, re, shlex, sys

AI_EXES = {"claude", "codex"}
RUNNERS = {"npx": None, "bunx": None, "uvx": None, "npm": {"i", "install", "exec", "x", "add"},
           "pnpm": {"dlx", "add", "i", "install", "exec"}, "yarn": {"dlx", "add"}, "pipx": {"run", "install"}}
WRAPPERS = {"env", "sudo", "nohup", "exec", "command", "time", "nice", "timeout", "xargs", "stdbuf"}
SHELLS = {"bash", "sh", "zsh", "dash"}
AI_PKG = re.compile(r"^(@anthropic-ai/|@openai/codex|claude(-code)?(@|$)|codex(@|$))")
CRED = re.compile(r"\.(claude|codex)(-account[0-9]+)?(/|\b)|(^|[\s/'\"=])auth\.json\b|\.credentials\.json\b|\b(ANTHROPIC|OPENAI)_API_KEY\b")
SEP = {";", "&&", "||", "|", "&", "\n", "(", ")", "|&"}

def tokens(text):
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return text.split()

def subcommands(text):
    """$(...) 和反引号里的命令单独拿出来再判断。"""
    return re.findall(r"\$\(([^()]*)\)", text) + re.findall(r"`([^`]*)`", text)

def ai_in_segment(seg):
    i = 0
    while i < len(seg) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[i]) or os.path.basename(seg[i]) in WRAPPERS
                            or (i > 0 and os.path.basename(seg[i - 1]) in WRAPPERS and seg[i].startswith("-"))):
        i += 1
    if i >= len(seg):
        return None
    exe = os.path.basename(seg[i]); rest = seg[i + 1:]
    if exe in AI_EXES:
        return f"执行 {exe}"
    if exe in SHELLS:
        for j, a in enumerate(rest):
            if a.startswith("-") and "c" in a and j + 1 < len(rest):
                return check_text(rest[j + 1])
        return None
    if exe in RUNNERS:
        subs = RUNNERS[exe]; args = rest
        if subs is not None:
            if not args or args[0] not in subs:
                return None
            args = args[1:]
        for a in args:
            if not a.startswith("-") and AI_PKG.match(a):
                return f"{exe} 装或运行 AI 包 {a}"
    return None

def check_text(text):
    toks = tokens(text); seg = []
    for t in toks + [";"]:
        if t in SEP or set(t) <= set(";&|()"):
            r = ai_in_segment(seg) if seg else None
            if r:
                return r
            seg = []
        else:
            seg.append(t)
    for sub in subcommands(text):
        r = check_text(sub)
        if r:
            return r
    return None

argv = sys.argv[1:]; full = " ".join(argv)
if CRED.search(full):
    print(f"凭据：{CRED.search(full).group(0).strip()}"); sys.exit(2)
r = ai_in_segment(argv) or check_text(shlex.join(argv))
if r:
    print(r); sys.exit(1)
