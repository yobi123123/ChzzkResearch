#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chzzk_probe.py — CHZZK(치지직) 내부 웹 API 재생 체인 재현 조사 스크립트

목적: 로그인/쿠키 없이, 치지직 웹이 쓰는 내부 GET API를 호출해
      라이브 상세 -> 재생 정보(livePlaybackJson) -> 마스터 m3u8 ->
      미디어 m3u8 -> 영상 조각(segment) 까지 어디까지 되는지 단계별로 확인한다.

안전장치:
  - 쿠키/토큰을 쓰지 않는다(세션마다 새로 만들고 쿠키를 비운다).
  - GET만 호출한다. 상태 변경(POST/PUT/DELETE)은 하지 않는다.
  - 영상 조각은 기본 2개만 받는다.
  - 요청 사이 최소 1.2초 간격.
  - 프록시는 선택 인자(--proxy). 기본값은 프록시 없음(이 환경 기본 출구 IP).

사용법:
  python3 chzzk_probe.py --channel <channelId>
  python3 chzzk_probe.py --live <liveId>          # 목록에서 channelId를 역조회
  python3 chzzk_probe.py --channel <id> --proxy http://host:port
  옵션: --segments N (기본 2), --header-test (헤더 영향 비교), --no-media (m3u8/조각 생략)

쿠키를 쓰는 기능은 의도적으로 넣지 않았다.
"""
import argparse, hashlib, json, re, sys, time
from urllib.parse import urlparse, parse_qs

try:
    import requests
except ImportError:
    sys.exit("requests 필요: pip install requests")

CHROME = "156"  # 데스크톱 Chrome 최신 메이저 (조사 시점)
UA = (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      f"(KHTML, like Gecko) Chrome/{CHROME}.0.0.0 Safari/537.36")
API_ORIGIN = "https://api.chzzk.naver.com"
API_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://chzzk.naver.com/",
    "Origin": "https://chzzk.naver.com",
    # 번들에서 확인된 치지직 전용 공통 헤더(비로그인에도 전송됨)
    "Front-Client-Product-Type": "web",
    "Front-Client-Platform-Type": "PC",
}
_last = [0.0]
def _throttle():
    dt = time.time() - _last[0]
    if dt < 1.2:
        time.sleep(1.2 - dt)
    _last[0] = time.time()

def new_session(proxy=None):
    s = requests.Session()
    s.cookies.clear()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s

def _send(sess, method, url, **kw):
    # 일시적 프록시/네트워크 끊김 재시도(지수 백오프). 정책 거부(4xx/5xx 응답)는 재시도하지 않음.
    last = None
    for i in range(4):
        try:
            return sess.request(method, url, **kw)
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
            last = e
            time.sleep(2 * (2 ** i))
    raise last

def req(sess, method, url, headers, stream=False, label=""):
    _throttle()
    r = _send(sess, method, url, headers=headers, timeout=30,
              allow_redirects=False, stream=stream)
    body = r.content if not stream else b""
    rec = {
        "label": label, "method": method, "url": url,
        "status": r.status_code,
        "content_type": r.headers.get("content-type", ""),
        "len": len(body),
        "sha256": hashlib.sha256(body).hexdigest() if body else "",
        "resp_headers": {k: r.headers.get(k) for k in
                         ("content-type", "x-cache", "cache-control", "server") if r.headers.get(k)},
    }
    return r, body, rec

def masked(u):
    """URL의 토큰/서명 값은 앞 8자만 남긴다."""
    def repl(m):
        k, v = m.group(1), m.group(2)
        if k.lower() in ("hdnts", "token", "sig", "signature", "pallycon", "hmac", "auth",
                         "policy", "key", "expires", "__token__"):
            return f"{k}={v[:8]}…" if len(v) > 8 else f"{k}={v}"
        return m.group(0)
    return re.sub(r"([A-Za-z0-9_]+)=([^&]+)", repl, u)

# ---------- 라이브 상세 (버전별) ----------
LD_VERSIONS = ["v1", "v2", "v2.1", "v3", "v3.3"]
def live_detail(sess, channel_id, ver):
    url = f"{API_ORIGIN}/service/{ver}/channels/{channel_id}/live-detail"
    r, body, rec = req(sess, "GET", url, API_HEADERS, label=f"live-detail {ver}")
    try:
        j = json.loads(body)
    except Exception:
        j = None
    content = (j or {}).get("content") if isinstance(j, dict) else None
    info = {"api_code": (j or {}).get("code"), "api_msg": (j or {}).get("message")}
    if isinstance(content, dict):
        for k in ("adult", "userAdultStatus", "status", "krOnlyViewing"):
            info[k] = content.get(k)
        info["has_playback"] = bool(content.get("livePlaybackJson"))
        info["playback"] = content.get("livePlaybackJson")
    rec["parsed"] = info
    return rec, content

# ---------- 토큰 기반 meta 엔드포인트(참고용 직접 호출) ----------
def playback_meta(sess, channel_id):
    out = []
    for url, label in [
        (f"{API_ORIGIN}/service/v3.3/channels/{channel_id}/live-detail-meta?dt=0", "live-detail-meta v3.3"),
        (f"{API_ORIGIN}/service/v1.1/channels/{channel_id}/live-playback-json-meta?tm=0", "live-playback-json-meta v1.1"),
    ]:
        r, body, rec = req(sess, "GET", url, API_HEADERS, label=label)
        rec["body_head"] = body[:400].decode("utf-8", "replace")
        out.append(rec)
    return out

# ---------- 재생 체인 ----------
def parse_playback(playback_json):
    pj = json.loads(playback_json) if isinstance(playback_json, str) else playback_json
    medias = pj.get("media", []) if isinstance(pj, dict) else []
    hls = None
    for m in medias:
        if m.get("mediaId") == "HLS" or "mpegurl" in str(m.get("mimeType", "")).lower() or m.get("path", "").endswith(".m3u8") or ".m3u8" in m.get("path", ""):
            hls = m
            break
    if hls is None and medias:
        hls = medias[0]
    return pj, hls

def fetch_master(sess, master_url):
    h = {"User-Agent": UA, "Referer": "https://chzzk.naver.com/", "Origin": "https://chzzk.naver.com",
         "Accept": "*/*"}
    r, body, rec = req(sess, "GET", master_url, h, label="master m3u8")
    text = body.decode("utf-8", "replace")
    rec["body_head"] = text[:1200]
    # 변형(화질)별 URL 추출
    variants = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("#EXT-X-STREAM-INF"):
            res = re.search(r"RESOLUTION=([0-9x]+)", ln)
            bw = re.search(r"BANDWIDTH=([0-9]+)", ln)
            uri = lines[i + 1] if i + 1 < len(lines) else ""
            variants.append({"resolution": res.group(1) if res else "?",
                             "bandwidth": int(bw.group(1)) if bw else 0,
                             "uri": uri.strip()})
    rec["variants"] = [{"resolution": v["resolution"], "bandwidth": v["bandwidth"]} for v in variants]
    return rec, variants

def resolve(base_url, uri):
    if uri.startswith("http"):
        return uri
    from urllib.parse import urljoin
    return urljoin(base_url, uri)

def fetch_media_and_segments(sess, media_url, n_seg):
    h = {"User-Agent": UA, "Referer": "https://chzzk.naver.com/", "Origin": "https://chzzk.naver.com",
         "Accept": "*/*"}
    r, body, rec = req(sess, "GET", media_url, h, label="media m3u8")
    text = body.decode("utf-8", "replace")
    rec["body_head"] = text[:1200]
    segs = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    seg_recs = []
    for seg in segs[:n_seg]:
        su = resolve(media_url, seg)
        rr, sb, srec = req(sess, "GET", su, h, label="segment")
        srec["body_head"] = ""
        seg_recs.append(srec)
    return rec, seg_recs

# ---------- 헤더 영향 비교 ----------
def header_test(sess, channel_id):
    url = f"{API_ORIGIN}/service/v3.3/channels/{channel_id}/live-detail"
    conds = {
        "(a) 필수 헤더 전부": API_HEADERS,
        "(b) User-Agent 없음": {k: v for k, v in API_HEADERS.items() if k != "User-Agent"},
        "(c) python-requests 기본 UA": {**{k: v for k, v in API_HEADERS.items() if k != "User-Agent"}},
        "(d) Mozilla/5.0 만": {"User-Agent": "Mozilla/5.0"},
        "(e) Referer·Origin 없음": {k: v for k, v in API_HEADERS.items() if k not in ("Referer", "Origin")},
    }
    out = []
    for name, h in conds.items():
        _throttle()
        s2 = new_session(sess_proxy[0])
        # (c)는 requests 기본 UA(python-requests/x.y)가 자동 부여됨
        r = _send(s2, "GET", url, headers=h, timeout=30)
        try:
            j = r.json(); code = j.get("code"); has = bool((j.get("content") or {}).get("livePlaybackJson"))
        except Exception:
            code = None; has = None
        out.append({"cond": name, "status": r.status_code, "api_code": code,
                    "sent_ua": r.request.headers.get("User-Agent"), "has_playback": has})
    return out

sess_proxy = [None]

def find_channel_by_live(sess, live_id):
    url = f"{API_ORIGIN}/service/v1/lives?size=50&sortType=POPULAR"
    r, body, rec = req(sess, "GET", url, API_HEADERS, label="lives")
    j = json.loads(body)
    for x in j["content"]["data"]:
        if str(x.get("liveId")) == str(live_id):
            return x["channel"]["channelId"]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel")
    ap.add_argument("--live")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--segments", type=int, default=2)
    ap.add_argument("--no-media", action="store_true")
    ap.add_argument("--header-test", action="store_true")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    sess_proxy[0] = args.proxy
    sess = new_session(args.proxy)

    channel = args.channel
    if not channel and args.live:
        channel = find_channel_by_live(sess, args.live)
        print(f"# live {args.live} -> channel {channel}")
    if not channel:
        sys.exit("--channel 또는 --live 필요")

    report = {"channel": channel, "proxy": args.proxy, "exit_ip": None, "steps": []}
    try:
        report["exit_ip"] = requests.get("https://ipinfo.io/json",
                                         proxies={"https": args.proxy} if args.proxy else None,
                                         timeout=15).json()
    except Exception:
        pass

    print(f"\n=== 라이브 상세 (버전별) : channel {channel} ===")
    content_full = None
    for ver in LD_VERSIONS:
        rec, content = live_detail(sess, channel, ver)
        p = rec["parsed"]
        print(f"[{ver:5}] HTTP {rec['status']} code={p.get('api_code')} "
              f"adult={p.get('adult')} userAdultStatus={p.get('userAdultStatus')} "
              f"status={p.get('status')} playback={p.get('has_playback')}")
        report["steps"].append(rec)
        if content and content.get("livePlaybackJson") and content_full is None:
            content_full = content

    print("\n=== 토큰 기반 meta 엔드포인트(직접 호출, 참고) ===")
    for rec in playback_meta(sess, channel):
        print(f"[{rec['label']}] HTTP {rec['status']} {rec['content_type']} :: {rec['body_head'][:160]}")
        report["steps"].append(rec)

    if args.header_test:
        print("\n=== 헤더 영향 비교 (v3.3 live-detail) ===")
        for row in header_test(sess, channel):
            print(f"{row['cond']:28} HTTP {row['status']} code={row['api_code']} "
                  f"playback={row['has_playback']} UA={str(row['sent_ua'])[:40]}")
            report["steps"].append({"label": "header-test", **row})

    if content_full and not args.no_media:
        print("\n=== 재생 체인 (playbackJson 있음) ===")
        pj, hls = parse_playback(content_full["livePlaybackJson"])
        if hls:
            master_url = hls.get("path")
            print(f"master: {masked(master_url)}")
            mrec, variants = fetch_master(sess, master_url)
            report["steps"].append(mrec)
            print(f"[master m3u8] HTTP {mrec['status']} 화질: {mrec.get('variants')}")
            if variants and mrec["status"] == 200:
                # 저화질/고화질 양쪽 시도
                targets = []
                vs = sorted(variants, key=lambda v: v["bandwidth"])
                targets.append(("저화질", vs[0]))
                if len(vs) > 1:
                    targets.append(("고화질", vs[-1]))
                for qlabel, v in targets:
                    mu = resolve(master_url, v["uri"])
                    print(f"\n-- {qlabel} {v['resolution']} --")
                    rec2, segs = fetch_media_and_segments(sess, mu, args.segments)
                    print(f"[media m3u8] HTTP {rec2['status']} {rec2['content_type']} len={rec2['len']}")
                    report["steps"].append(rec2)
                    for s in segs:
                        print(f"  [segment] HTTP {s['status']} {s['content_type']} "
                              f"len={s['len']} sha256={s['sha256'][:16]}")
                        report["steps"].append(s)
        else:
            print("HLS 미디어를 playbackJson에서 찾지 못함")
    elif not content_full:
        print("\n재생 정보(livePlaybackJson)를 받지 못함 — 재생 체인 생략")

    if args.json_out:
        json.dump(report, open(args.json_out, "w"), ensure_ascii=False, indent=1)
        print(f"\n# JSON 저장: {args.json_out}")

if __name__ == "__main__":
    main()
