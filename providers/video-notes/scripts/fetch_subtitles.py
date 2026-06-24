#!/usr/bin/env python3
"""视频字幕批量获取流水线 v2（需要 Python >= 3.10）

用法:
    python3 fetch_subtitles.py --workdir <目录>          # 读 <目录>/urls.txt 批量处理
    python3 fetch_subtitles.py --workdir <目录> <url>    # 处理单个链接
    python3 fetch_subtitles.py <url>                     # 单链接，工作区默认当前目录

工作区结构（由本脚本读写）:
    <workdir>/urls.txt          输入：一行一个链接（# 开头忽略）
    <workdir>/transcripts/*.md  输出：拉到的字幕文本（带时间戳）
    <workdir>/audio/*.m4a       输出：无字幕视频的音频，待 FunASR 转录
    <workdir>/转换报告.md        输出：本次批量处理结果汇总

凭据:
    B站 AI 字幕 / 音频下载需要登录态。凭据按以下顺序读取，均不写入工作区/不入库：
        1. ~/.config/video-notes-cookie.txt    （推荐，0600，不随云盘同步）
        2. <workdir>/cookie.txt                 （后备）
    文件内容为一整行 Cookie 头串：SESSDATA=xxx; bili_jct=xxx; buvid3=xxx; ...

平台支持:
    - bilibili: 直拉字幕（WBI 签名 + 登录态）；无字幕降级下音频待 FunASR。已端到端验证。
    - youtube : 用 yt-dlp 拉自动/人工字幕（需 --browser edge 提供登录态，已处理
                2026 年 n-challenge 反爬）。已验证。
    - douyin  : yt-dlp 原生支持（含 v.douyin.com 短链），无字幕→下音频待 FunASR。已验证。

零第三方 import（仅标准库）；yt-dlp 为可选外部命令（pip install yt-dlp）。
"""

import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import reduce
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

SLEEP_BETWEEN = 3  # 秒，批量时的请求间隔，降低风控概率
SUB_LANGS = "zh-Hans,zh-Hant,zh,en"  # YouTube 字幕优先语言

COOKIE_FILE_LOCAL = Path.home() / ".config" / "video-notes-cookie.txt"


# ---------------------------------------------------------------- 凭据

def load_cookie(workdir: Path) -> str:
    """优先读本机 ~/.config，后备读工作区 cookie.txt。返回 Cookie 头串。"""
    for f in (COOKIE_FILE_LOCAL, workdir / "cookie.txt"):
        if f.exists():
            lines = [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines()
                     if ln.strip() and not ln.strip().startswith("#")]
            if lines:
                return lines[-1]
    return ""


def cookie_to_netscape(cookie_header: str) -> str:
    """把 'a=b; c=d' 头串转成 Netscape cookie 文件内容。

    yt-dlp 用 --cookies 文件比 --add-header 'Cookie:' 更稳：实测后者会被
    B站风控判为 HTTP 412，前者正常下载。
    """
    out = ["# Netscape HTTP Cookie File"]
    for kv in cookie_header.split(";"):
        kv = kv.strip()
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        out.append(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{k.strip()}\t{v.strip()}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- HTTP

class FetchError(Exception):
    """带可读分类的网络错误，便于上层区分风控 / 鉴权 / 其它。"""


def http_get(url: str, cookie: str, referer: str = "https://www.bilibili.com") -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": referer,
        "Cookie": cookie,
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 412:
            raise FetchError("触发 B 站风控（HTTP 412）：降低频率或稍后重试，"
                             "或更新 cookie") from e
        if e.code in (401, 403):
            raise FetchError(f"鉴权失败（HTTP {e.code}）：cookie 可能已过期，请更新") from e
        raise FetchError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"网络错误: {e.reason}") from e


def http_get_json(url: str, cookie: str) -> dict:
    return json.loads(http_get(url, cookie).decode("utf-8"))


# ---------------------------------------------------------------- WBI 签名

# B站 WBI mixin key 的固定重排表
_MIXIN_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def _mixin_key(orig: str) -> str:
    return reduce(lambda s, i: s + orig[i], _MIXIN_TAB, "")[:32]


def get_wbi_keys(cookie: str) -> tuple[str, str]:
    nav = http_get_json("https://api.bilibili.com/x/web-interface/nav", cookie)
    img = nav["data"]["wbi_img"]
    img_key = img["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = img["sub_url"].rsplit("/", 1)[1].split(".")[0]
    return img_key, sub_key


def enc_wbi(params: dict, img_key: str, sub_key: str) -> str:
    mixin = _mixin_key(img_key + sub_key)
    params = dict(params)
    params["wts"] = int(time.time())
    params = dict(sorted(params.items()))
    params = {k: "".join(c for c in str(v) if c not in "!'()*")
              for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    params["w_rid"] = hashlib.md5((query + mixin).encode()).hexdigest()
    return urllib.parse.urlencode(params)


# ---------------------------------------------------------------- 工具

def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\n\r]', "_", name).strip()[:120]
    return cleaned or "未命名"


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    """返回目录下不冲突的路径；已存在则追加 _2、_3…，避免静默覆盖。"""
    p = directory / f"{stem}{suffix}"
    n = 2
    while p.exists():
        p = directory / f"{stem}_{n}{suffix}"
        n += 1
    return p


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------- bilibili

def resolve_b23(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.url
    except urllib.error.HTTPError as e:
        return e.url or url


def extract_bvid(url: str) -> str:
    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    if not m:
        raise ValueError(f"无法从链接中提取 BV 号: {url}")
    return m.group(1)


def pick_subtitle(subtitles: list) -> dict | None:
    """优先人工/UP主上传字幕，其次 AI 字幕；同类优先中文。"""
    if not subtitles:
        return None
    human = [s for s in subtitles if not s.get("lan", "").startswith("ai-")]
    pool = human or subtitles
    zh = [s for s in pool if s.get("lan", "").startswith(("zh", "ai-zh"))]
    return (zh or pool)[0]


def subtitle_json_to_md(data: dict) -> str:
    return "\n".join(
        f"[{fmt_ts(it.get('from', 0))}] {it.get('content', '').strip()}"
        for it in data.get("body", []))


def fetch_bilibili(url: str, ctx: "Ctx") -> dict:
    if "b23.tv" in url:
        url = resolve_b23(url)
    bvid = extract_bvid(url)
    cookie = ctx.cookie

    view = http_get_json(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", cookie)
    if view.get("code") != 0:
        return {"title": bvid, "status": "error",
                "detail": f"view API 返回 {view.get('code')}: {view.get('message')}"}

    info = view["data"]
    title = info["title"]
    pages = info.get("pages", [])
    multi_p = len(pages) > 1

    img_key, sub_key = ctx.wbi_keys(cookie)

    got_any = False
    for idx, page in enumerate(pages, 1):
        cid = page["cid"]
        # 多 P 时 part 可能为空，用页序号兜底，避免各分 P 落到同名文件互相覆盖
        part = page.get("part", "") or (f"P{idx}" if multi_p else "")
        q = enc_wbi({"bvid": bvid, "cid": cid}, img_key, sub_key)
        player = http_get_json(
            f"https://api.bilibili.com/x/player/wbi/v2?{q}", cookie)
        subs = (player.get("data", {}).get("subtitle", {}) or {}).get("subtitles", [])
        chosen = pick_subtitle(subs)
        if not chosen:
            continue
        sub_url = chosen.get("subtitle_url") or ""
        if not sub_url:
            continue
        if sub_url.startswith("//"):
            sub_url = "https:" + sub_url
        sub_data = json.loads(http_get(sub_url, cookie).decode("utf-8"))
        body = subtitle_json_to_md(sub_data)

        name = safe_filename(f"{title}_{part}" if multi_p and part else title)
        out = unique_path(ctx.transcripts, name, ".md")
        kind = "AI字幕" if chosen.get("lan", "").startswith("ai-") else "CC字幕"
        out.write_text(
            f"# {title}{('（' + part + '）') if multi_p and part else ''}\n\n"
            f"- 来源: {url}\n- 平台: bilibili\n"
            f"- 字幕类型: {kind}（{chosen.get('lan')}）\n"
            f"- 获取时间: {time.strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{body}\n",
            encoding="utf-8")
        got_any = True
        if multi_p:
            time.sleep(1)

    if got_any:
        return {"title": title, "status": "subtitle", "detail": "字幕已保存"}

    # 没有字幕 → 降级下载音频，待 FunASR
    hint = "" if cookie else "（未配置 cookie，AI 字幕可能因此拉不到，建议先配 cookie 重试）"
    audio_path = ctx.audio / f"{safe_filename(title)}.m4a"
    ok, err = download_audio(url, audio_path, ctx)
    if ok:
        return {"title": title, "status": "audio",
                "detail": f"无字幕{hint}，音频已存 audio/，待 FunASR 转录"}
    return {"title": title, "status": "error",
            "detail": f"无字幕{hint}，且音频下载失败：{err}"}


# ---------------------------------------------------------------- yt-dlp

YTDLP = [sys.executable, "-m", "yt_dlp"]


def has_ytdlp() -> bool:
    try:
        return subprocess.run(YTDLP + ["--version"],
                              capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def download_audio(url: str, out_path: Path, ctx: "Ctx") -> tuple[bool, str]:
    if not has_ytdlp():
        return False, "yt-dlp 未安装（pip install yt-dlp）"
    args = YTDLP + ["--js-runtimes", "node"]
    cookie_file = ctx.netscape_cookie_file()  # 用文件而非 header，避开 412 风控
    if cookie_file:
        args += ["--cookies", str(cookie_file)]
    elif ctx.browser:
        args += ["--cookies-from-browser", ctx.browser]
    args += ["-f", "ba/b", "-x", "--audio-format", "m4a",
             "-o", str(out_path), url]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return False, "下载超时（>15min）"
    if r.returncode == 0 and out_path.exists():
        return True, ""
    err = (r.stderr or "").strip().splitlines()
    return False, err[-1][:200] if err else "未知错误"


def fetch_douyin(url: str, ctx: "Ctx") -> dict:
    """抖音无公开字幕 API → 用 yt-dlp 下音频，待 FunASR 转录。"""
    if not has_ytdlp():
        return {"title": url, "status": "error", "detail": "yt-dlp 未安装"}
    before = set(ctx.audio.glob("*.m4a"))
    args = YTDLP + ["--js-runtimes", "node"]
    if ctx.browser:
        args += ["--cookies-from-browser", ctx.browser]
    args += ["-f", "ba/b", "-x", "--audio-format", "m4a",
             "-o", str(ctx.audio / "%(title).80s_%(id)s.%(ext)s"), url]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return {"title": url, "status": "error", "detail": "下载超时"}
    new = sorted(set(ctx.audio.glob("*.m4a")) - before,
                 key=lambda p: p.stat().st_mtime)
    if new:
        return {"title": new[-1].stem, "status": "audio",
                "detail": "抖音无字幕，音频已存 audio/，待 FunASR 转录"}
    err = (r.stderr or "").strip().splitlines()
    hint = "" if ctx.browser else "（抖音下载通常需登录态，可加 --browser edge 重试）"
    return {"title": url, "status": "error",
            "detail": f"音频下载失败{hint}：{err[-1][:200] if err else '未知错误'}"}


def srt_to_md(srt_text: str) -> str:
    lines, out, last = srt_text.splitlines(), [], None
    i = 0
    while i < len(lines):
        if "-->" in lines[i]:
            ts = lines[i].split("-->")[0].strip().split(",")[0]
            ts = re.sub(r"^00:", "", ts)
            i += 1
            texts = []
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                texts.append(lines[i].strip())
                i += 1
            content = " ".join(texts)
            if content and content != last:  # 自动字幕常有重复行
                out.append(f"[{ts}] {content}")
                last = content
        i += 1
    return "\n".join(out)


def fetch_youtube(url: str, ctx: "Ctx") -> dict:
    if not has_ytdlp():
        return {"title": url, "status": "error", "detail": "yt-dlp 未安装"}
    tmp = ctx.workdir / ".yt_tmp"
    shutil.rmtree(tmp, ignore_errors=True)  # 入口清空，避免上次残留 srt 被误当本次结果（张冠李戴）
    tmp.mkdir(exist_ok=True)
    args = YTDLP + ["--js-runtimes", "node"]
    if ctx.browser:
        args += ["--cookies-from-browser", ctx.browser]
    # --ignore-no-formats-error：2026 年 YouTube 的 n-challenge 常导致取不到视频
    # 格式，但只下字幕（--skip-download）不该因此中止；该 flag 让字幕照常写出。
    # --ignore-errors：某个语言（如 zh-Hans）拿不到时不中止，继续试 en 等其它语言。
    args += ["--ignore-no-formats-error", "--ignore-errors",
             "--write-subs", "--write-auto-subs", "--sub-langs", SUB_LANGS,
             "--skip-download", "--convert-subs", "srt",
             "-o", str(tmp / "%(title)s.%(ext)s"), url]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"title": url, "status": "error", "detail": "拉字幕超时"}
    srts = sorted(tmp.glob("*.srt"), key=lambda p: p.stat().st_mtime)
    if not srts:
        return {"title": url, "status": "error",
                "detail": f"未拉到字幕: {(r.stderr or '').strip()[-200:]}"}
    srt = srts[-1]
    title = srt.name.rsplit(".", 2)[0]
    md = srt_to_md(srt.read_text(encoding="utf-8"))
    out = unique_path(ctx.transcripts, safe_filename(title), ".md")
    out.write_text(
        f"# {title}\n\n- 来源: {url}\n- 平台: youtube\n"
        f"- 获取时间: {time.strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{md}\n",
        encoding="utf-8")
    for f in tmp.glob("*"):
        f.unlink()
    return {"title": title, "status": "subtitle", "detail": "字幕已保存"}


# ---------------------------------------------------------------- 运行上下文

class Ctx:
    """承载工作区路径、凭据、惰性缓存的 WBI key 与临时 cookie 文件。"""

    def __init__(self, workdir: Path, browser: str = ""):
        self.workdir = workdir
        self.transcripts = workdir / "transcripts"
        self.audio = workdir / "audio"
        self.transcripts.mkdir(parents=True, exist_ok=True)
        self.audio.mkdir(parents=True, exist_ok=True)
        self.cookie = load_cookie(workdir)
        self.browser = browser
        self._wbi: tuple[str, str] | None = None
        self._cookie_file: Path | None = None
        # 进程被 SIGTERM/SIGKILL 之外的方式退出时兜底清理临时 cookie 文件
        atexit.register(self.cleanup)

    def wbi_keys(self, cookie: str) -> tuple[str, str]:
        if self._wbi is None:
            self._wbi = get_wbi_keys(cookie)
        return self._wbi

    def netscape_cookie_file(self) -> Path | None:
        """把 cookie 头串落成临时 Netscape 文件（0600），供 yt-dlp 用。"""
        if not self.cookie:
            return None
        if self._cookie_file is None:
            fd, path = tempfile.mkstemp(prefix="vn_cookies_", suffix=".txt")
            p = Path(path)
            os.close(fd)
            p.chmod(0o600)
            p.write_text(cookie_to_netscape(self.cookie), encoding="utf-8")
            self._cookie_file = p
        return self._cookie_file

    def cleanup(self):
        if self._cookie_file and self._cookie_file.exists():
            self._cookie_file.unlink()


# ---------------------------------------------------------------- 主流程

def detect_platform(url: str) -> str:
    if "bilibili.com" in url or "b23.tv" in url:
        return "bilibili"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "douyin.com" in url or "iesdouyin.com" in url:
        return "douyin"
    return "unknown"


def process(url: str, ctx: Ctx) -> dict:
    platform = detect_platform(url)
    try:
        if platform == "bilibili":
            result = fetch_bilibili(url, ctx)
        elif platform == "youtube":
            result = fetch_youtube(url, ctx)
        elif platform == "douyin":
            result = fetch_douyin(url, ctx)
        else:
            result = {"title": url, "status": "error", "detail": "无法识别的平台"}
    except Exception as e:  # 单条失败不阻塞批量
        result = {"title": url, "status": "error", "detail": f"{type(e).__name__}: {e}"}
    result["url"] = url
    result["platform"] = platform
    return result


def write_report(results: list, report_file: Path, cookie: str = ""):
    ok = sum(1 for r in results if r["status"] == "subtitle")
    aud = sum(1 for r in results if r["status"] == "audio")
    # 纵深防御：万一某条 detail 里混进了 cookie 值（如异常消息），写报告前脱敏
    secrets = [s for s in [cookie] + [
        kv.split("=", 1)[1] for kv in cookie.split(";")
        if kv.strip().startswith("SESSDATA=")] if s]

    def scrub(text: str) -> str:
        for s in secrets:
            text = text.replace(s, "***")
        return text

    rows = "\n".join(
        f"| {r['title']} | {r['platform']} | {r['status']} | {scrub(str(r['detail']))} |"
        for r in results)
    report_file.write_text(
        f"# 转换报告 {time.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"共 {len(results)} 条：字幕直拉 {ok}，待转录音频 {aud}，"
        f"其他 {len(results) - ok - aud}\n\n"
        f"| 标题 | 平台 | 状态 | 说明 |\n|---|---|---|---|\n{rows}\n\n"
        f"## 下一步\n\n"
        f"- `audio/` 里的文件：对 Claude 说「用 funasr 把 audio 里的音频转成文字」\n"
        f"- `transcripts/` 里的文件：对 Claude 说「把 transcripts 里的新字幕做成学习笔记」\n",
        encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="批量获取视频字幕")
    ap.add_argument("url", nargs="?", help="单个链接；省略则读 <workdir>/urls.txt")
    ap.add_argument("--workdir", default=".", help="工作区目录（默认当前目录）")
    ap.add_argument("--browser", default="", help="yt-dlp 读取登录态的浏览器（如 edge/chrome），可选")
    args = ap.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    if not workdir.exists():
        print(f"工作区不存在: {workdir}")
        sys.exit(1)

    if args.url:
        urls = [args.url]
    else:
        urls_file = workdir / "urls.txt"
        if not urls_file.exists():
            print(f"未找到 {urls_file}，请先创建并填入链接（一行一个）")
            sys.exit(1)
        urls = [ln.strip() for ln in urls_file.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    if not urls:
        print("没有有效链接")
        sys.exit(1)

    ctx = Ctx(workdir, browser=args.browser)
    print(f"工作区: {workdir}")
    print(f"共 {len(urls)} 个链接，cookie {'已' if ctx.cookie else '未'}配置，开始处理…\n")
    results = []
    try:
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url}")
            r = process(url, ctx)
            icon = {"subtitle": "✅", "audio": "🎧", "error": "❌"}.get(r["status"], "❓")
            print(f"    {icon} {r['title']} — {r['detail']}")
            results.append(r)
            if i < len(urls):
                time.sleep(SLEEP_BETWEEN)
    finally:
        ctx.cleanup()

    write_report(results, workdir / "转换报告.md", cookie=ctx.cookie)
    print(f"\n完成。报告已写入 {workdir / '转换报告.md'}")


if __name__ == "__main__":
    main()
