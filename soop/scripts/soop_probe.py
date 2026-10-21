#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
soop_probe.py — SOOP(숲, 옛 아프리카TV) 라이브 재생 체인 조사/재현 스크립트

목적: 로그인/쿠키 없이 SOOP 웹 내부 API를 호출해, 방송 '형태'별로
      재생정보 → HLS 마스터 → 미디어 → 영상 조각(.TS) 까지 어디까지 되는지,
      막히면 무엇이 막는지(RESULT 코드)를 단계별로 확인한다.

안전/방침:
  - 쿠키/토큰을 쓰지 않는다(세션마다 새로 만들고 쿠키를 비운다).
  - 재생정보 조회용 POST(player_live_api)만 쓴다. 상태 변경(팔로우/채팅/후원 등)은 호출하지 않는다.
  - 비밀번호는 추측/대입하지 않는다. --pwd 는 "사용자 본인이 아는 값"을 넣을 때만 쓰며 기본은 빈 값.
  - 영상 조각은 기본 2개만 받는다. 요청 간 1.2초 간격. 재시도는 네트워크 오류에 한함.
  - 프록시는 선택 인자(--proxy). 기본값은 프록시 없음(현재 출구 IP).

사용법:
  python3 soop_probe.py --bid <BJ_ID> --bno <BROAD_NO>
  python3 soop_probe.py --bid <BJ_ID> --bno <BROAD_NO> --segments 2 --json-out out.json
  python3 soop_probe.py --list            # 인기 라이브를 유형 플래그와 함께 나열(샘플 찾기용)
  python3 soop_probe.py --bid .. --bno .. --proxy http://host:port

RESULT 코드(관측):
   1  = 재생 가능 (비번 방송도 메타는 1이지만 AID 단계에서 비번 필요)
  -6  = 성인(19) — 로그인/성인인증 필요
  -14 = 구독 전용 — 구독 티어 필요 (P_MIN_TIER)
   0  = 오프라인/스트림 없음 (또는 비번 불일치 시 AID 단계)
"""
import argparse, hashlib, json, re, sys, time
from urllib.parse import quote, urljoin

try:
    import requests
except ImportError:
    sys.exit("requests 필요: pip install requests")

CHROME = "156"
UA = (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      f"(KHTML, like Gecko) Chrome/{CHROME}.0.0.0 Safari/537.36")
HDR = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
       "Referer": "https://www.sooplive.co.kr/", "Origin": "https://www.sooplive.co.kr",
       "Accept-Language": "ko-KR,ko;q=0.9"}
PLAYER_API = "https://live.sooplive.co.kr/afreeca/player_live_api.php"
RMD_DEFAULT = "https://livestream-manager.sooplive.com"
LIST_API = "https://live.sooplive.co.kr/api/main_broad_list_api.php"

RESULT_MEANING = {
    "1": "재생 가능(비번이면 AID에 pwd 필요)", "0": "오프라인/스트림없음 또는 비번불일치",
    "-6": "성인(19)·로그인/성인인증 필요", "-14": "구독 전용(티어 필요)",
}
_last = [0.0]
_proxy = [None]
def _throttle():
    dt = time.time() - _last[0]
    if dt < 1.2:
        time.sleep(1.2 - dt)
    _last[0] = time.time()

def _call(method, url, headers, data=None, stream=False):
    _throttle()
    last = None
    for i in range(5):
        try:
            s = requests.Session(); s.cookies.clear()
            if _proxy[0]:
                s.proxies = {"http": _proxy[0], "https": _proxy[0]}
            return s.request(method, url, headers=headers, data=data, timeout=25,
                             allow_redirects=False, stream=stream)
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
            last = e; time.sleep(1.5 * (2 ** i))
    raise last

def rec_of(r, body, label):
    return {"label": label, "url": r.request.url, "status": r.status_code,
            "content_type": r.headers.get("content-type", ""), "len": len(body),
            "sha256": hashlib.sha256(body).hexdigest() if body else ""}

def mask(u):
    return re.sub(r"(aid=)([^&]{8})[^&]+", r"\1\2…",
                  re.sub(r"(\.A32\.[A-Za-z0-9_\-]{8})[A-Za-z0-9_\-.]+", r"\1…", u))

def player_live(bid, bno, typ="live", pwd="", quality="original"):
    data = {"bid": bid, "bno": bno, "type": typ, "player_type": "html5",
            "stream_type": "common", "quality": quality, "mode": "landing",
            "from_api": "0", "pwd": pwd, "is_revive": "false"}
    h = dict(HDR); h["Content-Type"] = "application/x-www-form-urlencoded"
    r = _call("POST", PLAYER_API, h, data=data)
    body = r.content
    try:
        ch = json.loads(body).get("CHANNEL", {})
    except Exception:
        ch = {"_raw": body[:200].decode("utf-8", "replace")}
    return rec_of(r, body, f"player_live_api type={typ}"), ch

def stream_assign(bno, cdn="gcp_cdn", quality="master", rmd=RMD_DEFAULT):
    bk = f"{bno}-common-{quality}-hls"
    url = (f"{rmd}/broad_stream_assign.html?return_type={cdn}&use_cors=false"
           f"&cors_origin_url=play.sooplive.co.kr&broad_key={bk}")
    h = dict(HDR); h["Accept"] = "*/*"
    r = _call("GET", url, h); body = r.content
    try:
        view = json.loads(body).get("view_url")
    except Exception:
        view = None
    return rec_of(r, body, f"broad_stream_assign {quality}"), view

def fetch_text(url, label):
    h = dict(HDR); h["Accept"] = "*/*"
    r = _call("GET", url, h); body = r.content
    return rec_of(r, body, label), body.decode("utf-8", "replace")

def run(bid, bno, pwd="", n_seg=2, report=None):
    report = report if report is not None else {"steps": []}
    # 1) metadata (type=live): classify the gate
    rec, ch = player_live(bid, bno, "live", pwd)
    report["steps"].append({**rec, "RESULT": ch.get("RESULT"),
                            "flags": {k: ch.get(k) for k in ("BPWD", "GRADE", "P_MIN_TIER", "ISSP", "geo_cc") if k in ch}})
    res = str(ch.get("RESULT"))
    print(f"[player_live_api type=live] HTTP {rec['status']} RESULT={res} "
          f"({RESULT_MEANING.get(res, '?')})  flags={report['steps'][-1]['flags']}")
    if res != "1":
        print("  => 재생정보 거부. 스트림 단계 진입 불가.")
        return report
    if str(ch.get("BPWD")) == "Y" and not pwd:
        print("  => 비밀번호 방송(BPWD=Y). 비번 없이는 AID 발급 안 됨(우회 시도 안 함).")
    # 2) AID
    rec2, ch2 = player_live(bid, bno, "aid", pwd)
    aid = ch2.get("AID")
    report["steps"].append({**rec2, "RESULT": ch2.get("RESULT"), "aid_present": bool(aid)})
    print(f"[player_live_api type=aid ] HTTP {rec2['status']} RESULT={ch2.get('RESULT')} AID={'있음' if aid else '없음'}")
    if not aid:
        print("  => AID 미발급. 스트림 불가.")
        return report
    # 3) stream assign (master)
    recA, view = stream_assign(bno, ch.get("CDN", "gcp_cdn"), "master", ch.get("RMD", RMD_DEFAULT))
    print(f"[broad_stream_assign master] HTTP {recA['status']} view_url={mask(view or '')}")
    report["steps"].append({**recA, "view_url": mask(view or "")})
    if not view:
        return report
    # 4) master m3u8 (?aid=)
    master = view + "?aid=" + quote(aid)
    recM, txt = fetch_text(master, "master m3u8")
    print(f"[master m3u8] HTTP {recM['status']} len={recM['len']}")
    report["steps"].append(recM)
    variants = []
    lines = txt.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("#EXT-X-STREAM-INF"):
            res_ = re.search(r"RESOLUTION=([0-9x]+)", l)
            bw = re.search(r"BANDWIDTH=([0-9]+)", l)
            uri = lines[i + 1] if i + 1 < len(lines) else ""
            variants.append({"resolution": res_.group(1) if res_ else "?",
                             "bandwidth": int(bw.group(1)) if bw else 0, "uri": uri.strip()})
    print("  변형(화질):", [(v["resolution"], v["bandwidth"]) for v in variants])
    if not variants or recM["status"] != 200:
        return report
    for qlabel, v in ([("저화질", min(variants, key=lambda x: x["bandwidth"])),
                       ("고화질", max(variants, key=lambda x: x["bandwidth"]))]
                      if len(variants) > 1 else [("단일", variants[0])]):
        mu = urljoin(master, v["uri"])
        recme, mt = fetch_text(mu, f"media m3u8 {qlabel}")
        print(f"  -- {qlabel} {v['resolution']} -- media m3u8 HTTP {recme['status']} len={recme['len']}")
        report["steps"].append(recme)
        segs = [x.strip() for x in mt.splitlines() if x.strip() and not x.startswith("#")]
        for s in segs[:n_seg]:
            su = urljoin(mu, s)
            recs, _ = fetch_text(su, "segment")
            print(f"     [segment] HTTP {recs['status']} {recs['content_type']} "
                  f"len={recs['len']} sha256={recs['sha256'][:16]}")
            report["steps"].append(recs)
    return report

def list_lives(n=60):
    h = dict(HDR)
    r = _call("GET", LIST_API + "?selectType=action&orderType=view_cnt&pageNo=1&lang=ko_KR", h)
    j = json.loads(r.content)
    print(f"total_cnt={j.get('total_cnt')}  (page 1, {len(j.get('broad', []))}건)")
    print(f"{'broad_no':>10} {'bj_id':<16} grade pwd sub  title")
    for b in j.get("broad", [])[:n]:
        print(f"{b['broad_no']:>10} {b['user_id']:<16} "
              f"{str(b.get('broad_grade')):>4} {b.get('is_password'):>3} "
              f"{str(b.get('subscription_only')):>3}  {b.get('broad_title','')[:28]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bid"); ap.add_argument("--bno")
    ap.add_argument("--pwd", default="", help="본인이 아는 비번만. 기본 빈값(추측 금지)")
    ap.add_argument("--segments", type=int, default=2)
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--json-out")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    _proxy[0] = args.proxy
    if args.list:
        list_lives(); return
    if not (args.bid and args.bno):
        sys.exit("--bid 와 --bno 필요 (또는 --list)")
    report = {"bid": args.bid, "bno": args.bno, "proxy": args.proxy, "steps": []}
    try:
        report["exit_ip"] = requests.get("https://ipinfo.io/json",
                                         proxies={"https": args.proxy} if args.proxy else None,
                                         timeout=15).json()
    except Exception:
        pass
    print(f"=== SOOP 재생 체인: bid={args.bid} bno={args.bno} ===")
    run(args.bid, args.bno, args.pwd, args.segments, report)
    if args.json_out:
        json.dump(report, open(args.json_out, "w"), ensure_ascii=False, indent=1)
        print(f"\n# JSON 저장: {args.json_out}")

if __name__ == "__main__":
    main()
