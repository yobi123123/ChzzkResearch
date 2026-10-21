# SOOP(숲, 옛 아프리카TV) 내부 웹 API 전수조사 — 해외 IP·비로그인 기준

- 조사일: **2026-10-21 ~ 10-22 (KST)**
- 출구 IP: **160.79.106.137 / 미국(US, Ohio) / AS396982 Google LLC**
- 조건: **네이버/SOOP 로그인 없음, 쿠키 없음**(세션마다 쿠키 비움). 상태 변경(팔로우·채팅·후원 등) POST/PUT/DELETE **미호출**. **재생정보 조회용 POST(player_live_api)만 허용**. 비밀번호는 추측·대입하지 않음(빈 값으로만 관찰). 영상 조각은 시험용 2개만 수신. 요청 간 ≥1.2초.
- 방침: **우회는 하지 않고, "우회 가능성이 있는지"만** 응답 코드·구조 근거로 판정.
- 사실/추정 표기: `[확인함]` = 실제 호출로 확인, `[추정]` = 코드/구조에서 읽었으나 미호출.

> chzzk 조사(`report/CHZZK_API_전수조사_해외IP_20261021.md`)와 같은 형식. **핵심 차이**: SOOP은 재생정보를 **POST(`player_live_api.php`)**로 받고, HLS 스트림은 **AID 토큰**을 거쳐 접근한다.

---

## 1. 요약 (Q1~Q5)

### Q1. SOOP 웹이 쓰는 내부 API는 무엇이고, 로그인이 필요한가?
SOOP은 해외 IP에서 웹 접속 시 국내 `www.sooplive.co.kr` → **글로벌 `www.sooplive.com`(Next.js)으로 301 리다이렉트**된다 `[확인함]`. 그러나 **실제 데이터 API(`*.sooplive.co.kr`)는 해외 IP에서 그대로 직접 호출된다** `[확인함]`. 핵심 호스트/엔드포인트(§3):
- `live.sooplive.co.kr/api/main_broad_list_api.php` — 라이브 목록(비로그인 OK, 3,700+건) `[확인함]`
- `live.sooplive.co.kr/afreeca/player_live_api.php` — **재생정보(POST)**. `type=live`(메타)·`type=aid`(토큰) `[확인함]`
- `livestream-manager.sooplive.com/broad_stream_assign.html` — HLS 뷰 URL 할당 `[확인함]`
- `live-global-cdn-v02.sooplive.co.kr` — **라이브 HLS(.m3u8/.TS)**, `?aid=` 토큰 필요 `[확인함]`
- `api.m.sooplive.co.kr` — 모바일 API(라이브/VOD 목록, VOD 재생정보) `[확인함]`
목록·메타데이터 계열 GET은 비로그인 OK. 팔로우·채팅·후원·설정 등은 로그인 필요 `[추정]`.

### Q2. 해외 IP·비로그인에서 방송 형태별로 어디까지 되는가?
방송 **형태별로 결과가 갈린다** `[확인함]`:

| 형태 | player_live_api RESULT | 다운로드(영상 조각) | 막는 지점 |
|---|---|---|---|
| **일반 라이브** | `1` | **✅ 됨** (360p~1080p .TS 수신) | 없음 |
| **성인(19) 라이브** | `-6` | ❌ 안 됨 | 재생정보 자체 거부 |
| **비밀번호 라이브** | `1`(메타) → aid `0` | ❌ 안 됨 | AID 토큰 발급에 비번 필요 |
| **구독 전용 라이브** | `-14` | ❌ 안 됨 | 재생정보 거부(티어 필요) |
| **일반 VOD(다시보기)** | (별도 API) | **✅ 됨** (HLS 마스터 수신) | 없음 |
| **성인 VOD** | — | ❌ (비로그인 목록에 비노출) | 목록·조회 단계 |

**일반 라이브·일반 VOD는 해외·비로그인으로 완전히 받아진다. 성인·구독은 재생정보 단계에서, 비밀번호는 AID 토큰 단계에서 막힌다.**

### Q3. 막는 주체와 이유는?
막는 주체는 **SOOP API 서버**(`player_live_api.php`)다. 이유는 형태별로 다르며 모두 **로그인/권한 기반이고 지역 기반이 아니다** `[확인함]`:
- 성인: `RESULT=-6` (성인인증·로그인 필요)
- 구독: `RESULT=-14`, `P_MIN_TIER=2` (구독 티어 필요)
- 비번: 메타는 `RESULT=1`이나 **AID 발급에 비번 필요**(빈 비번 → `RESULT=0`, AID 없음)
서버는 우리 요청을 `geo_cc=US`로 인식하면서도 **일반 방송은 정상 재생**시켰다 → **해외 IP 자체 차단은 아니다** `[확인함]`. (웹 프런트의 `.com` 리다이렉트는 '포털'만 해외용으로 돌릴 뿐, 데이터/스트림 API는 해외 IP를 막지 않음.)

### Q4. 우회 가능성이 있는가? (우회는 하지 않음, 가능성만 판정)
- **성인·구독**: 재생정보(AID 포함) 자체를 서버가 내주지 않으므로 **비로그인 우회 가능성 없음** `[확인함]`. 다른 버전·대체 경로를 찾지 못함.
- **비밀번호**: **메타데이터는 비번 없이 노출**(`RESULT=1`, 제목·BJ·플래그)되나, **스트림 토큰(AID)은 비번 없이는 `RESULT=0`으로 거부** → 비번을 모르면 재생 불가. 즉 "**정보 누출은 있으나 스트림 게이트는 서버측에서 유지**". 비번을 추측·대입하면 뚫릴 수 있는 종류이나(그건 우회이므로 시도하지 않음), **빈 비번으로는 열리지 않음** `[확인함]`.
- 종합: **클라이언트 조작만으로(로그인·비번·구독 없이) 성인/구독/비번 방송을 받는 길은 확인되지 않음**.

### Q5. 헤더가 응답을 바꾸는가?
`player_live_api`·목록 API는 데스크톱 Chrome UA + `Referer/Origin: sooplive.co.kr`로 호출했고 정상 동작 `[확인함]`. (chzzk와 달리 SOOP은 POST form·AID 흐름이 본질이라, 헤더보다 **파라미터(type, pwd)와 로그인 상태**가 응답을 가른다.) ※ 본 환경 제약: 출구 프록시가 `*.sooplive` 호스트에 **간헐적 연결 리셋**을 일으켜 재시도(지수 백오프)를 넣었다. 라이브러리 기본 UA 차단 이슈는 chzzk 조사 §5와 동일하게 존재할 수 있어 다른 망에서 재검증 권장(§11).

**최종 결론**: 해외 US IP·비로그인으로 **SOOP 일반 라이브와 일반 VOD는 영상 조각까지 완전히 다운로드 가능**하다. 반면 **성인(−6)·구독 전용(−14)은 재생정보 단계에서, 비밀번호 방송은 AID 토큰 단계에서 서버가 차단**한다. 막는 것은 **지역이 아니라 로그인/연령·구독·비밀번호 권한**이며, 비로그인 상태의 클라이언트 조작 우회 경로는 확인되지 않았다.

---

## 2. 시험 환경

| 항목 | 값 |
|---|---|
| 출구 IP / 국가 / ASN | 160.79.106.137 / US(Ohio) / AS396982 Google LLC `[확인함]` |
| 시험 시각 | 2026-10-21 23:30 ~ 2026-10-22 00:45 KST |
| 도구 | Python 3.13 + requests 2.34, curl 8.5 |
| 쿠키 | 없음(세션마다 비움). API 호출에 `Set-Cookie` 의존 없음 |
| 웹 프런트 | `www.sooplive.co.kr` → **`www.sooplive.com`(Next.js) 301**(해외 라우팅). 데이터 API는 `.co.kr` 직접 사용 |
| 서버 인식 | `player_live_api` 응답에 `geo_cc=US`, `svc_lang=ko_KR` — 서버가 해외임을 알고도 일반 방송 허용 |

**쓴 요청 헤더**(재생정보 POST):
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Referer: https://www.sooplive.co.kr/
Origin: https://www.sooplive.co.kr
Content-Type: application/x-www-form-urlencoded   (POST)
```
(HLS .m3u8/.TS 요청은 `Accept: */*`, 나머지 동일)

---

## 3. API 목록 (정적·동적 분석)

> SOOP 웹 플레이어의 핵심 로직은 해외용 `.com`(Next.js) 번들에 **포함되어 있지 않아**(해외 포털은 축소판), **엔드포인트는 실제 호출로 동적 확인**했다 `[확인함]`.

| 메서드 | 호스트 | 경로 | 용도 | 로그인 | 성인/게이트 | 근거 |
|---|---|---|---|---|---|---|
| GET | live.sooplive.co.kr | /api/main_broad_list_api.php?selectType=..&pageNo=.. | 라이브 목록 | 불필요 | `broad_grade`,`is_password`,`subscription_only`,`parent_broad_no` | 호출 |
| GET | api.m.sooplive.co.kr | /broad/a/list?orderType=..&pageNo=.. | 모바일 라이브 목록 | 불필요 | `grade`,`is_password` | 호출 |
| **POST** | live.sooplive.co.kr | **/afreeca/player_live_api.php** (`type=live`) | **재생 메타·게이트 판정** | 성인/구독=필요 | `RESULT`,`BPWD`,`GRADE`,`P_MIN_TIER` | 호출 |
| **POST** | live.sooplive.co.kr | /afreeca/player_live_api.php (`type=aid`) | **스트림 토큰(AID)** | 성인/구독/비번=필요 | `AID` | 호출 |
| GET | livestream-manager.sooplive.com | /broad_stream_assign.html?...&broad_key={bno}-common-{q}-hls | HLS 뷰 URL 할당 | 불필요(일반) | — | 호출 |
| GET | live-global-cdn-v02.sooplive.co.kr | /{stream}/auth_master_playlist.m3u8?aid=.. | **라이브 HLS 마스터** | AID 필요 | — | 호출 |
| GET | live-global-cdn-v02.sooplive.co.kr | /{stream}/auth_playlist.m3u8?aid=.. · *.TS | 미디어/영상 조각 | AID 필요 | — | 호출 |
| **POST** | api.m.sooplive.co.kr | /station/video/a/view (`nTitleNo`) | **VOD 재생정보** | 성인=필요 | `grade`,`files[].file` | 호출 |
| GET | api.m.sooplive.co.kr | /station/video/a/list | VOD 목록 | 불필요 | `grade`(성인 비노출) | 호출 |
| GET | vod-normal-global-cdn-z02.sooplive.co.kr | /.../{file}.smil/.../manifest.m3u8 | **VOD HLS** | 불필요(일반) | — | 호출 |

보조 호스트(관측): `liveimg.sooplive.co.kr`(썸네일), `res.sooplive.com`(정적), `chat-*.sooplive.com`/`colony.sooplive.com`(채팅), `reqde.sooplive.com`(광고), `chapi.sooplive.co.kr`(채널 API). 공식 오픈 API는 `openapi.sooplive.co.kr`(별도, 미조사).

**방송 형태 분류 필드**(목록/`player_live_api`): `broad_grade`(0=전체, 19=성인), `is_password`(N/Y), `subscription_only`(0/2), `parent_broad_no`(≠0=중계방), `broad_type`(21/30/31=인코더 종류 등), `allowed_view_cnt`, `P_MIN_TIER`(구독 최소 티어), `BPWD`(비번 여부).

---

## 4. 방송 형태별 단계 결과 (핵심, 3단계)

표본: 887개 라이브 스캔(§evidence `kr_lives2.json` 기준) — `broad_grade` 0:823 / 19:64, `is_password=Y` 소수, `subscription_only≠0` 소수, `parent_broad_no≠0` 0건.

| 형태 | 샘플(bid/bno) | type=live RESULT | type=aid | stream_assign | master m3u8 | 영상 조각 | 판정 |
|---|---|---|---|---|---|---|---|
| **일반** | khm11903 / 298011215 | `1` (BPWD=N,GRADE=0) | AID 발급 | 200 view_url | **200** (1080/720/540/360) | **200 ×2 (video/MP2T, 360p·1080p)** | **다운로드 가능** `[확인]` |
| **성인(19)** | eunyoung1238 / 298014537 | **`-6`** | (진입X) | — | — | — | 재생정보 거부 `[확인]` |
| **성인(19)** | sunaang / 298016905 | **`-6`** | (진입X) | — | — | — | 동일 `[확인]` |
| **비밀번호** | iamquaddurup / 298009481 | `1` (**BPWD=Y**) | **RESULT=0, AID 없음** | — | — | — | 토큰 단계 차단 `[확인]` |
| **구독 전용** | beadyo97 / 298001997 | **`-14`** (**P_MIN_TIER=2**) | (진입X) | — | — | — | 재생정보 거부 `[확인]` |
| **구독+성인** | rmlrl771 / 298017919 | **`-6`** | (진입X) | — | — | — | 성인 게이트 우선 `[확인]` |

일반 방송 영상 조각(.TS) 상세 `[확인]`:
- 360p: HTTP 200 `video/MP2T` 182,172B(sha `2a02d0fef052fa2b…`), 186,496B(`d7e6eb56feb0c941…`)
- 1080p: HTTP 200 `video/MP2T` 2,110,488B(`c7633fc48f5c6fb0…`), 4,265,908B(`db817b3b33c2a2e6…`)

**중계방(parent≠0)·유료(입장료) 라이브**: 표본(887건)에서 발견되지 않아 미시험(§11).

---

## 5. 재생 체인 (일반 방송 — 해외·비로그인으로 동작 확인)

1. `POST player_live_api.php` `type=live&bid=..&bno=..` → `RESULT=1`, `RMD`, `CDN`, `BPWD`, `geo_cc` 등
2. `POST player_live_api.php` `type=aid&...&quality=original` → `CHANNEL.AID`(스트림 토큰)
3. `GET {RMD}/broad_stream_assign.html?return_type={CDN}&broad_key={bno}-common-master-hls` → `view_url`(= `auth_master_playlist.m3u8`)
4. `GET {view_url}?aid={AID}` → 마스터 m3u8(화질별 `auth_playlist.m3u8?aid=..`)
5. `GET {미디어 m3u8}` → `*.TS` 조각 목록
6. `GET {*.TS}` → `video/MP2T`

- 필수: 2·4·5·6 단계에 **AID 토큰**(2에서 획득). `broad_key`의 품질 토큰은 `original/hd/sd/master`(= `auto`는 오류).
- 토큰: AID는 `.A32.`로 시작하는 서명 문자열(만료 시 2단계부터 재발급). CDN은 `gcp_cdn`(해외), `view_url`은 `live-global-cdn-v02.sooplive.co.kr`.

---

## 6. 근거 발췌 (실제 요청/응답)

### 6-1. 일반 라이브 — 재생정보(POST) RESULT=1
```
2026-10-22 00:44 KST
POST https://live.sooplive.co.kr/afreeca/player_live_api.php
 body: bid=khm11903&bno=298011215&type=live&player_type=html5&stream_type=common&quality=original&mode=landing&pwd=
HTTP 200 application/json
 CHANNEL(발췌): RESULT=1, BPWD=N, GRADE=0, CDN=gcp_cdn, RMD=https://livestream-manager.sooplive.com,
                geo_cc=US, svc_lang=ko_KR, VIEWPRESET=[360p/480p/720p/1080p], AID(type=aid 시 별도)
```
(전체 필드: `evidence/sample_channel_normal.json`, 토큰 마스킹)

### 6-2. 일반 라이브 — AID → 마스터 m3u8 → 조각
```
POST player_live_api.php type=aid  → CHANNEL.AID = .A32.pxqRXFP…   (스트림 토큰)
GET  broad_stream_assign.html ...broad_key=298011215-common-master-hls
     → {"result":"1","view_url":"https://live-global-cdn-v02.sooplive.co.kr/live-stmc-40/auth_master_playlist.m3u8"}
GET  auth_master_playlist.m3u8?aid=.A32.pxqRXFP…  → HTTP 200
     #EXT-X-STREAM-INF:...RESOLUTION=1920x1080  auth_playlist.m3u8?aid=..
     (화질: 1080/720/540/360)
GET  ...640x360/298011215-common-sd-hls_7925_....TS  → HTTP 200 video/MP2T 186,496B
```

### 6-3. 성인(19) — 재생정보 거부
```
POST player_live_api.php type=live  bid=eunyoung1238 bno=298014537
HTTP 200 → CHANNEL: {"RESULT":-6, "ISSP":0, "geo_cc":"US", ... (AID/RMD/TS 없음)}
```

### 6-4. 비밀번호 방송 — 메타는 노출, AID는 거부
```
POST type=live  bid=iamquaddurup bno=298009481
  → RESULT=1, BPWD=Y, 제목/BJ 등 메타 노출 (AID/TS 없음)
POST type=aid   (pwd 빈 값)
  → {"CHANNEL":{"RESULT":0,"GDPR":false}}   ← AID 미발급(비번 필요). 우회 시도 안 함.
```

### 6-5. 구독 전용 — 재생정보 거부
```
POST type=live  bid=beadyo97 bno=298001997
  → {"CHANNEL":{"RESULT":-14, "P_MIN_TIER":"2", "TIER_TYPE":0}}   ← 구독 티어2 필요
```

### 6-6. VOD(다시보기) — 일반은 재생 가능
```
POST https://api.m.sooplive.co.kr/station/video/a/view  body: nTitleNo=139894599&nApiLevel=11&nPlaylistIdx=0
  → result=1, data.grade=0, files[0].file=https://vod-normal-global-cdn-z02.sooplive.co.kr/.../....smil/
GET  {file}  → HTTP 200 application/x-mpegURL (마스터 m3u8, 화질 variants)   ← 비로그인 재생 가능
성인 VOD: 비로그인 목록(station/video/a/list)에 grade=19가 노출되지 않음 → 조회 단계에서 가려짐
```

---

## 7. 막힌 원인 분석 (4단계)

| 형태 | 막는 지점 | 코드/근거 | 지역 요인? |
|---|---|---|---|
| 성인(19) | player_live_api(type=live) | `RESULT=-6` | ❌ (일반은 같은 IP서 재생) |
| 구독 전용 | player_live_api(type=live) | `RESULT=-14`, `P_MIN_TIER` | ❌ |
| 비밀번호 | player_live_api(type=aid) | `RESULT=0`(빈 비번) | ❌ |
| 성인 VOD | VOD 목록/조회 | 비로그인 목록 비노출 | ❌ |

모두 **로그인/권한(연령·구독·비밀번호) 기반**이며, 해외 IP라서 막힌 사례는 없었다. 서버는 `geo_cc=US`로 인식하면서도 일반 라이브·일반 VOD를 **해외 글로벌 CDN(`*-global-cdn-*`)으로 정상 서빙**했다 → SOOP의 해외 대응은 "**웹 포털만 .com으로 분기**, 스트림 API는 비차단"으로 보인다 `[확인함]`. (단, 스트리머가 켤 수 있는 '해외 시청 제한' 개별 설정 방송은 표본에서 못 만나 미확인 — §11.)

---

## 8. 우회 가능성 판정 (요청하신 항목)

- **성인·구독**: 비로그인으로는 재생정보(AID 포함)가 서버에서 아예 안 나옴. 다른 API 버전·대체 경로도 못 찾음 → **클라이언트 조작 우회 가능성 확인 안 됨**.
- **비밀번호**: 메타데이터(제목·BJ·플래그)는 비번 없이 노출되는 **정보 누출**이 있으나, **스트림 토큰은 서버가 비번으로 보호**(빈 비번 불가). 비번 자체를 추측·대입하는 건 '우회'이므로 시도하지 않았고, **정상 범위(빈 비번)에서는 열리지 않음**.
- 공통: AID·CDN 토큰은 서버 서명 기반이라 재사용/위조 징후는 조사 범위 밖(시도 안 함). 결론적으로 **로그인·권한 없이 받아지는 건 일반 라이브·일반 VOD뿐**이다.

---

## 9. 확인하지 못한 것 / 다른 IP·환경에서 재검증할 항목

1. **중계방(parent_broad_no≠0)·유료(입장료) 라이브**: 표본 887건에 없어 미시험. 라이브 시 샘플 확보해 재확인 필요.
2. **스트리머 '해외 시청 제한' 설정 방송**: 해당 설정을 켠 방송을 못 만남. 이것이 해외 IP를 실제로 막는 유일한 경로일 수 있으므로, 그런 방송을 찾아 재확인 필요(이 경우에만 지역 차단이 성립).
3. **성인 VOD의 정확한 거부 코드**: 비로그인 목록 비노출까지만 확인. 직접 `title_no`로 조회 시 코드 확인 필요.
4. **Catch(숏폼)·클립**: 엔드포인트를 빠르게 찾지 못해 미시험(`catch/a/list` 404/500). 별도 확인 필요.
5. **라이브러리 기본 UA/헤더 민감도**: 본 환경 프록시 제약으로 chzzk와 동일 수준의 UA 비교는 다른 망에서 재검증 권장.
6. **한국 IP에서 성인/구독/비번**: 비로그인이면 동일하게 막힐 것으로 추정(게이트가 로그인 기반) — 한국 IP로 직접 재확인 권장.
7. **AID 만료 시간·재사용 가능 범위**: 미측정.

---

## 10. 재현 방법

스크립트: `soop/scripts/soop_probe.py` (부록 B에 전문). 쿠키 없음. 재생정보 POST만. 비번 추측 안 함.

```bash
pip install requests

# 인기 라이브를 유형 플래그와 함께 나열(샘플 찾기)
python3 soop/scripts/soop_probe.py --list

# 방송 재생 체인 확인 (bid=BJ아이디, bno=방송번호)
python3 soop/scripts/soop_probe.py --bid <BJ_ID> --bno <BROAD_NO> --segments 2 --json-out out.json

# 다른 IP에서 같은 시험
python3 soop/scripts/soop_probe.py --bid <BJ_ID> --bno <BROAD_NO> --proxy http://HOST:PORT
```
결과 읽는 법: `type=live` 줄의 `RESULT` 값으로 게이트를 판정한다 — `1`=재생 가능, `-6`=성인, `-14`=구독, 비번은 `RESULT=1 BPWD=Y`이나 `type=aid`에서 `RESULT=0`. 일반 방송은 `master → media → segment`가 모두 `HTTP 200`, 조각에 `video/MP2T`와 sha256이 찍힌다.

---

## 11. 부록 A: 조사한 호스트·엔드포인트 요약
- 웹: `www.sooplive.co.kr`(→ `.com` 301), `www.sooplive.com`(Next.js 포털)
- 목록: `live.sooplive.co.kr/api/main_broad_list_api.php`, `api.m.sooplive.co.kr/broad/a/list`
- 재생정보(POST): `live.sooplive.co.kr/afreeca/player_live_api.php` (`type=live`/`type=aid`)
- 스트림 할당: `livestream-manager.sooplive.com/broad_stream_assign.html`
- 라이브 HLS: `live-global-cdn-v02.sooplive.co.kr/*/auth_master_playlist.m3u8?aid=`
- VOD: `api.m.sooplive.co.kr/station/video/a/{view,list}`, `vod-normal-global-cdn-z02.sooplive.co.kr/*.smil/*/manifest.m3u8`
- 원본 호출 로그: `evidence/recon_http_log.jsonl`(94건, 토큰 마스킹), 프로브 결과: `evidence/probe_*.json`, 샘플 응답: `evidence/sample_channel_normal.json`

---

## 12. 부록 B: 재현 스크립트 전문 (`soop/scripts/soop_probe.py`)

```python
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

```

