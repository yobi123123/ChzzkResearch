# 치지직(CHZZK) 내부 웹 API 전수조사 — 해외 IP·비로그인 기준

- 조사일: **2026-10-21 ~ 10-22 (KST)**
- 조사 환경 출구 IP: **160.79.106.137 / 미국(US, Ohio) / AS396982 Google LLC** (ipinfo.io 조회)
- 조건: **네이버/치지직 로그인 없음, 쿠키 없음**(세션마다 쿠키 비움). 상태 변경 요청(POST/PUT/DELETE)은 호출하지 않음. GET만 호출. 영상 조각은 시험용 2개만 수신.
- 이 보고서 한 개만 읽어도 결론 검토와 재현이 가능하도록 작성함. 판단 근거가 된 요청/응답은 본문(§7)과 부록에 직접 넣음.
- **사실/추정 구분**: 문장 끝 `[확인함]` = 실제 호출로 확인, `[추정]` = 번들 코드에서 읽었으나 호출로 확인하지 않음.

---

## 1. 요약 (Q1~Q5)

### Q1. 치지직 웹이 쓰는 내부 API는 무엇이고, 로그인이 필요한가?
치지직 웹 프런트(`chzzk.naver.com`)는 **axios 인스턴스 24종**으로 다음 호스트/베이스를 호출한다 `[확인함, 번들 정적분석]`:
`api.chzzk.naver.com`의 `/service/{v1,v1.1,v2,v2.1,v3,v3.3}`, `/manage/{v1,v2}`, `/commercial/v1`, `/polling/{v1,v3.1}`, `/ad-polling/v1` 그리고 `comm-api.game.naver.com/nng_main/{v1,v2}`(채팅·알림·신고), `apis.naver.com/nng_main/nng_comment_api/v1`(댓글), `esports-api.game.naver.com`, `openapi.chzzk.naver.com`(공식 오픈 API). 번들에서 추출한 호출 지점은 **303개**(§3 표, 부록 A 전체 목록). 이 중 **조회(GET)계 공개 API는 비로그인·쿠키 없이도 200 OK로 동작**한다(라이브 목록, 채널 정보, 라이브 상세, 검색, 카테고리, VOD 목록 등) `[확인함]`. `/manage/*`, `/commercial/*`, 팔로우·채팅·후원 등 **개인·상태성 API는 로그인(쿠키) 필요** `[추정, 경로/용도 기준]`. 로그인 상태는 `comm-api.game.naver.com/nng_main/v1/user/getUserStatus`로 확인한다 `[확인함, 번들]`.

### Q2. 해외 IP·비로그인에서 성인 방송은 어느 단계까지 되는가?
- **라이브 상세**: `adult=true`인 방송도 `live-detail`(v2/v3/v3.3) 자체는 **HTTP 200**으로 열린다. 단 **`livePlaybackJson = null`**, `userAdultStatus = NOT_LOGIN_USER` `[확인함, 성인 방송 3건]`.
- **재생 정보 → 그 이후 전부 불가**: 재생 JSON을 주는 토큰 엔드포인트 `GET /service/v1.1/channels/{id}/live-playback-json-meta`가 **HTTP 403, `code 9009`, "미성년자는 시청이 불가능합니다."** 로 차단 `[확인함]`. 따라서 **마스터 m3u8 · 미디어 m3u8 · 영상 조각 단계로 넘어갈 재생 정보 자체를 얻지 못한다.** 결론: **성인 방송은 '라이브 상세(메타데이터)'까지만 되고 '재생 정보'부터 막힌다.**
- 대조군(일반 방송)은 동일 조건에서 **라이브 상세 → playbackJson → 마스터 m3u8 → 미디어 m3u8 → 영상 조각(144p·1080p 양쪽)까지 전부 200 OK** `[확인함]`.

### Q3. 막는 주체와 이유는?
막는 주체는 **치지직/네이버 API 서버**(`server: nfront`)이고, 이유는 **연령 인증(성인 인증) 미충족 — 비로그인**이다. 근거: 재생 정보 요청에 대한 **403 / code 9009 / "미성년자는 시청이 불가능합니다."** `[확인함]`. 비로그인 사용자를 서버가 '미성년(미인증)'으로 간주해 재생 JSON을 내주지 않는 방식이다. **지역(해외 IP) 차단이 아니다** — 같은 해외 IP에서 일반 방송은 재생 조각까지 완전히 받아진다(§6에서 지역 가설 반증) `[확인함]`. `krOnlyViewing` 필드는 성인·일반 모두 `false`였다 `[확인함]`.

### Q4. 성인 재생 정보를 얻을 다른 경로가 있는가?
시험한 대체 경로 **모두 같은 연령 게이트로 막힘** `[확인함]`:
`live-detail` v1(500/9004 — 버전 미지원), v2·v3·v3.3(200이나 `livePlaybackJson=null`), `live-detail-meta` v3.3(200이나 playback 없음), `live-playback-json-meta` v1.1(**403/9009**), `live/{id}/auto-play-info`(200이나 `livePlaybackJson=null`, `previewPlaybackJson=null`). 웹 번들에는 **성인 방송용 별도 재생 경로나 임베드 라이브 플레이어 경로가 존재하지 않는다**(`/embed/*`는 클립 전용) `[확인함, 번들]`. 공식 오픈 API에도 **시청용 재생 URL 엔드포인트가 아예 없다**(브로드캐스터 송출용 `streamKey`만 있음) `[확인함, 문서]`. 성인 **VOD/다시보기**도 동일하게 `inKey/videoId`가 비로그인 시 `null`로 막힘 `[확인함]`.

### Q5. 헤더가 응답을 바꾸는가? 필수 헤더는?
치지직 내부 `live-detail` API는 **특별한 헤더를 요구하지 않는다** `[확인함]`. User-Agent 없음 / Referer·Origin 없음 / `Mozilla/5.0`만 — **전부 200 OK, 일반 방송 playback 정상 수신**. 성인 게이트(403/9009)는 **헤더와 무관하며 로그인 상태에만 좌우**된다 `[확인함]`. 번들이 붙이는 치지직 전용 공통 헤더 `Front-Client-Product-Type`, `Front-Client-Platform-Type`, `deviceId` 등이 있으나(§2·§5) **없어도 응답이 동일**했다. m3u8·영상 조각 요청도 실제 브라우저와 동일하게 `Referer: https://chzzk.naver.com/`를 넣어 200을 받았다(미설정 비교는 §11의 미확인 항목). ※ 본 환경 고유 제약: 출구 프록시가 `python-requests/*`·`curl/*` 같은 **라이브러리 기본 UA를 치지직 도달 전에 차단**(연결 리셋)하므로 그 두 조건은 이 환경에서 검증 불가(§5·§11).

**최종 결론**: 해외 IP·로그인/쿠키 없음 상태에서 **일반 방송은 재생(영상 조각 수신)까지 완전히 가능**하지만, **성인 방송은 '재생 정보(playbackJson)'를 서버가 연령 인증(로그인) 미충족을 이유로 403으로 거부**하여 **영상 조각은 물론 마스터 m3u8조차 얻을 수 없다.** 막는 것은 **지역이 아니라 로그인/성인인증**이다.

---

## 2. 시험 환경

| 항목 | 값 |
|---|---|
| 출구 IP | 160.79.106.137 `[확인함, ipinfo.io]` |
| 국가/도시 | US / Columbus, Ohio |
| ASN / 망 | AS396982 **Google LLC** (클라우드) |
| 시험 시각 | 2026-10-21 23:55 ~ 2026-10-22 00:15 KST (= 10-21 14:55~15:15 UTC) |
| 도구 | Python 3.13.16 + requests 2.34.2, curl 8.5.0, Chromium 141(미사용), Playwright 1.55(설치만) |
| 쿠키 조건 | **쿠키 없음**. 치지직 홈/API 응답에 `Set-Cookie` **없음** → 사이트가 주는 익명 쿠키(NNB 등)도 발급되지 않았으므로 "쿠키 없음"과 "익명 쿠키만" 조건이 **동일** `[확인함]` |
| 네트워크 제약 | 출구가 에이전트 프록시 경유. **라이브러리 기본 UA(`python-requests`, `curl`)는 프록시가 리셋**함(치지직이 아니라 본 환경) `[확인함]` |

**실제로 쓴 요청 헤더 전체** (API 호출):
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Referer: https://chzzk.naver.com/
Origin: https://chzzk.naver.com
Front-Client-Product-Type: web
Front-Client-Platform-Type: PC
```
(m3u8·영상 조각 요청은 `Accept: */*`, 나머지 동일)

---

## 3. API 목록 (1단계 정적 분석 요약)

API 베이스는 번들의 axios 인스턴스 정의에서 확정했다 `[확인함]`:
`to(e,t)` 매핑 — `LIVE_SERVICE→api.chzzk.naver.com/service/{ver}`, `LIVE_MANAGE→/manage/{ver}`, `LIVE_COMMERCIAL→/commercial/v1`, `POLLING→/polling/{ver}`, `AD_POLLING→/ad-polling/v1`, `NNG→comm-api.game.naver.com/nng_main/{ver}`, `COMMENT→apis.naver.com/nng_main/nng_comment_api/v1`, `ESPORTS→esports-api.game.naver.com/service/{ver}`, `OPEN_API→openapi.chzzk.naver.com/open/v1`.

재생·성인 판단에 핵심이 되는 API만 발췌(전체 303개는 부록 A):

| 메서드 | 호스트 | 경로(버전) | 용도 | 로그인 | 성인 관련 | 근거 |
|---|---|---|---|---|---|---|
| GET | api.chzzk.naver.com | /service/v1/lives?{q} | 라이브 목록 | 불필요 `[확인]` | 응답에 `adult` 플래그 | 번들 `$p` / 호출 |
| GET | api.chzzk.naver.com | /service/{v2,v3,v3.3}/channels/{id}/live-detail | 라이브 상세·재생정보 | 불필요(열람)/성인은 재생 withhold | `adult`,`userAdultStatus`,`livePlaybackJson` | 호출 |
| GET | api.chzzk.naver.com | /service/v3.3/channels/{id}/live-detail-meta?dt={t} | 라이브 상세(토큰형) | 불필요 | playback 없음(성인) | 번들 `em`/`Np` 터널링 |
| GET | api.chzzk.naver.com | /service/v1.1/channels/{id}/live-playback-json-meta?tm={t} | **재생 JSON(토큰형)** | 성인=로그인 필요 | **403/9009** | 번들 `nm`/`Np` · 호출 |
| GET | api.chzzk.naver.com | /service/v1/live/{liveId}/auto-play-info | 자동재생 미리보기 | 불필요 | 성인=null | 번들 · 호출 |
| GET | api.chzzk.naver.com | /polling/v3.1/channels/{id}/live-status | 라이브 상태 폴링 | 불필요 | 재생 아님 | 번들 `tm` |
| GET | api.chzzk.naver.com | /service/v1/channels/{id} | 채널 정보 | 불필요 | - | 번들 · 호출 |
| GET | api.chzzk.naver.com | /service/v3/videos/{videoNo} | VOD 상세·재생키 | 성인=로그인 필요 | `inKey`,`videoId` null | 호출 |
| GET | api.chzzk.naver.com | /service/v1/play-info/{type}/{id} | **클립** 재생정보 | - | contentType=clip 전용 | 번들 `Lz('clip',..)` |
| GET | api.chzzk.naver.com | /service/v1/search/{lives,videos,channels} | 검색 | 불필요 | 결과에 adult | 호출 |
| GET | comm-api.game.naver.com | /nng_main/v1/user/getUserStatus | 로그인 상태 | (비로그인=loggedIn:false) | - | 번들 `$s` |
| GET | comm-api.game.naver.com | /nng_main/v1/chats/access-token | 채팅 토큰 | - | - | 번들 |
| GET | openapi.chzzk.naver.com | /open/v1/lives | (공식)라이브 목록 | 앱 client 인증 | adult 플래그 | 공식 문서 |
| GET | openapi.chzzk.naver.com | /open/v1/streams/key | (공식)**송출**키 | 유저 토큰 | 시청용 아님 | 공식 문서 |

전체 호스트(번들 문자열 빈도순): `chzzk.naver.com`, `api.chzzk.naver.com`, `game.naver.com`, `comm-api.game.naver.com`, `apis.naver.com`, `esports-api.game.naver.com`, `nga.naver.com`(활동로그), `routing.chat.naver.com`(채팅 라우팅), `kr-col-ext.nelo.navercorp.com`(로그수집), `openapi/developers.chzzk.naver.com`, `pay.naver.com`/`wallet.pay.naver.com`(결제), `video-phinf/nng-phinf.pstatic.net`(이미지), `livecloud.akamaized.net`(영상 CDN).

---

## 4. 공개 GET 호출 결과 (2단계)

| API | HTTP | code | 응답 최상위 키 | 비로그인 시 비는 필드 | 비고 |
|---|---|---|---|---|---|
| /service/v1/lives?size=50&sortType=POPULAR | 200 | 200 | code,message,content{size,page,data} | — | 50건, 각 항목에 `adult` 불리언 `[확인]` |
| /service/v1/channels/{id} | 200 | 200 | content{...} | 개인화 필드 | `[확인]` |
| /service/**v1**/channels/{id}/live-detail | **500** | **9004** | (오류) | 전부 | **v1은 live-detail 미지원** `[확인]` |
| /service/v2/channels/{id}/live-detail | 200 | 200 | content{livePlaybackJson,...} | (일반)없음 | `[확인]` |
| /service/v2.1/.../live-detail | **404** | — | (없음) | — | v2.1 경로 없음 `[확인]` |
| /service/v3/.../live-detail | 200 | 200 | content{livePlaybackJson,...} | — | `[확인]` |
| /service/v3.3/.../live-detail | 200 | 200 | content{livePlaybackJson, userAdultStatus,...} | 성인=playback,userAdultStatus=NOT_LOGIN_USER | 웹이 실제 사용 `[확인]` |
| /service/v1.1/channels/{id}/live-playback-json-meta?tm=0 | 200(일반)/**403**(성인) | 200/**9009** | content{playbackJson} | — | **더미 토큰 `tm=0`에도 일반은 재생JSON 반환** `[확인]` |
| /service/v3.3/channels/{id}/live-detail-meta?dt=0 | 200 | 200 | content{...} | playback(성인) | 더미 `dt=0` 수용 `[확인]` |
| /service/v1/live/{liveId}/auto-play-info | 200 | 200 | content{livePlaybackJson,previewPlaybackJson,...} | 성인=모두 null | `[확인]` |
| /service/v3/videos/{videoNo} | 200 | 200 | content{inKey,videoId,adult,vodStatus,...} | 성인=inKey/videoId null | `[확인]` |
| /service/v1/channels/{id}/videos?size=10 | 200 | 200 | content{data[]} | — | `[확인]` |
| /service/v1/search/videos?keyword=19 | 200 | 200 | content{data[]} | — | `[확인]` |

주요 버전 차이: **v1은 live-detail을 지원하지 않고(500/9004), v2.1 경로는 없다(404).** 실사용 버전은 **v2/v3/v3.3**이며 재생정보 구조(`livePlaybackJson`)는 동일했다. 토큰형(`*-meta`)은 더미 토큰(`tm=0`,`dt=0`)으로도 일반 콘텐츠 재생 JSON을 반환했다 — 즉 **터널링 토큰은 성인 게이트를 여는 열쇠가 아니다**(성인은 토큰과 무관하게 403) `[확인함]`.

---

## 5. 헤더 영향 (Q5)

대상: `GET /service/v3.3/channels/{id}/live-detail` (일반=랄로 채널, 성인=1건). 각 조건 1회.

| 조건 | 대상 | HTTP | api code | playback 수신 | 비고 |
|---|---|---|---|---|---|
| (a) 필수 헤더 전부 | 일반 | 200 | 200 | True | 기준 `[확인]` |
| (b) User-Agent 없음 | 일반 | 200 | 200 | True | UA 불필요 `[확인]` |
| (c) `python-requests/2.34.2` UA | 일반 | **000** | — | 측정불가 | **본 환경 프록시가 리셋**(치지직 미도달) `[확인]` |
| (d) `Mozilla/5.0`만 | 일반 | 200 | 200 | True | 최소 UA로 충분 `[확인]` |
| (e) Referer·Origin 없음 | 일반 | 200 | 200 | True | Referer/Origin 불필요 `[확인]` |
| (f) curl 기본 UA(`curl/8.5.0`) | 일반 | **000** | — | 측정불가 | **본 환경 프록시가 리셋** `[확인]` |
| (a) 필수 헤더 전부 | 성인 | 200 | 200 | **False** | 성인 playback은 헤더 무관 null `[확인]` |
| (b) User-Agent 없음 | 성인 | 200 | 200 | **False** | 동일 `[확인]` |

결론: 치지직 `live-detail`은 **헤더 게이트가 없다**. (c)·(f)의 `000`은 **치지직 응답이 아니라 본 세션 출구 프록시의 UA 차단**이다(대조 확인: UA 끝에 `python` 글자가 있어도 `Mozilla/5.0...python`은 200 → 차단 대상은 `python-requests/*`·`curl/*` 패턴 자체). 일반 네트워크에서 재검증 필요(§11). CORS 응답 헤더는 `access-control-allow-origin: https://chzzk.naver.com` + `allow-credentials: true`로 **chzzk.naver.com 출처에 한정**된다(브라우저 정책용, 서버측 접근제어는 아님) `[확인]`.

---

## 6. 성인 방송 단계별 결과 (3단계, 핵심)

성인 방송 2건 + 비교용 일반 1건. (한국시간 심야 시간대, 성인 라이브 다수 송출 중)

| 방송(채널ID 앞6 / liveId / 시각KST) | 라이브상세 v2/v3/v3.3 | 재생정보(playbackJson) | live-playback-json-meta v1.1 | 마스터 m3u8 | 미디어 m3u8 | 영상 조각 | 화질 | 비고 |
|---|---|---|---|---|---|---|---|---|
| **일반** 3497a9 / 21771179 / 10-22 00:04 | 200, adult=false | **있음** | 200, playbackJson 반환 | **200** | **200** | **200 ×2(144p·1080p)** | 144/360/480/720/1080 | **완전 재생 가능** `[확인]` |
| **성인** feb20a / 21769833 / 10-22 00:06 | 200, adult=true, userAdultStatus=NOT_LOGIN_USER | **null** | **403 / 9009 "미성년자는 시청이 불가능합니다."** | — (진입불가) | — | — | — | 재생정보부터 차단 `[확인]` |
| **성인** 8a933c / 21764767 / 10-22 00:07 | 200, adult=true, userAdultStatus=NOT_LOGIN_USER | **null** | **403 / 9009 동일** | — | — | — | — | 동일 `[확인]` |
| **성인VOD** (검색) / videoNo 15281077 | v3 videos:200, adult=true, userAdultStatus=NOT_LOGIN_USER | inKey=null, videoId=null, vodStatus=NONE | (해당없음) | — | — | — | — | VOD도 동일 게이트 `[확인]` |

일반 방송 재생 조각 상세 `[확인]`:
- 144p 조각 2개: HTTP 200, `video/mp4`, 50,763B(sha256 `dfd93b1bd087174a…`), 47,502B(`23260258bce0354f…`)
- 1080p 조각 2개: HTTP 200, `video/mp4`, 2,027,659B(`659cbae360dbfd84…`), 2,036,330B(`0e055b1e2a35f052…`)
- **저화질·고화질 모두 열림** (마스터에 144~1080 전 화질 노출).

같은 성인 방송을 시점을 바꿔 재호출해도 결과 동일(403 고정). 토큰 만료·일시 현상이 아니라 **구조적 연령 게이트** `[확인]`.

---

## 7. 근거 발췌 (실제 요청/응답)

### 7-1. 일반 방송 — 재생정보 수신 (livePlaybackJson)
```
시각: 2026-10-22 00:04 KST
GET https://api.chzzk.naver.com/service/v3.3/channels/3497a9a7221cc3ee5d3f95991d9f95e9/live-detail
요청 헤더: UA(Chrome 156), Accept: application/json..., Referer/Origin: https://chzzk.naver.com, Front-Client-*
HTTP/2 200 · content-type: application/json · server: nfront
응답 content.livePlaybackJson (발췌):
  "meta":{"videoId":"8E3176454C1CDAF173443B12173018FB4D44","streamSeq":27588676,
          "liveId":"21771179","paidLive":false,"cdnInfo":{"cdnType":"GCDN"},"playbackAuthType":"NONE"}
  "media":[{"mediaId":"HLS","protocol":"HLS","path":"https://livecloud.akamaized.net/chzzk/lip2_kr/.../_hls_playlist.m3u8?hdnts=st=1792…",
            "encodingTrack":[{"720p high 3000000"},{"480p main 1500000"},{"360p main 600000"} ...]},
           {"mediaId":"LLHLS", ...}]
```

### 7-2. 일반 방송 — 마스터 m3u8 (토큰 포함)
```
시각: 2026-10-22 00:05 KST
GET https://livecloud.akamaized.net/chzzk/lip2_kr/cflexnmss2u0006/suhbp52fbgquxoujmznl7yirybeewbah46it/…_hls_playlist.m3u8?hdnts=st=17925…
요청 헤더: UA(Chrome 156), Accept: */*, Referer: https://chzzk.naver.com/
HTTP 200 · 본문:
  #EXTM3U
  #EXT-X-VERSION:7
  #EXT-X-INDEPENDENT-SEGMENTS
  #EXT-X-STREAM-INF:BANDWIDTH=3192000,CODECS="avc1.640028,mp4a.40.2",RESOLUTION=1280x720,FRAME-RATE=60.00
  hdntl=exp=1792656379~acl=*%2f…%2f*~data=hdntl~hmac=2750a847835c457d…/720p/…_hls_chunklist.m3u8
  #EXT-X-STREAM-INF:...RESOLUTION=852x480...  (480p)
  ... 256x144, 640x360, 1920x1080 ...
토큰: 마스터 URL = ?hdnts=st=<시작>…  / 변형 chunklist = hdntl=exp=1792656379(~ KST 2026-10-22 17:06 만료)~hmac=<64hex>
```

### 7-3. 일반 방송 — 미디어 m3u8 + 영상 조각
```
GET …/720p 또는 /1080p …_hls_chunklist.m3u8  → HTTP 200, application/x-mpegURL (len≈2.6KB)
GET …segment.mp4  → HTTP 200, video/mp4
  144p: 50,763B sha256 dfd93b1bd087174a… / 47,502B sha256 23260258bce0354f…
  1080p: 2,027,659B sha256 659cbae360dbfd84… / 2,036,330B sha256 0e055b1e2a35f052…
```

### 7-4. 성인 방송 — 라이브 상세는 200이나 재생정보 null
```
시각: 2026-10-22 00:06 KST
GET https://api.chzzk.naver.com/service/v3.3/channels/feb20a676694b1163fed010da0848303/live-detail
HTTP/2 200 · server: nfront · access-control-allow-origin: https://chzzk.naver.com
응답 content(발췌): "adult":true, "userAdultStatus":"NOT_LOGIN_USER", "status":"OPEN",
                    "livePlaybackJson":null, "previewPlaybackJson":null, "krOnlyViewing":false
```

### 7-5. 성인 방송 — 재생정보 요청이 403으로 차단 (핵심 근거)
```
시각: 2026-10-22 00:06 KST
GET https://api.chzzk.naver.com/service/v1.1/channels/feb20a676694b1163fed010da0848303/live-playback-json-meta?tm=0
요청 헤더: UA(Chrome 156), Referer/Origin: https://chzzk.naver.com
HTTP 403 · content-type: application/json
응답 본문(전문): {"code":9009,"message":"미성년자는 시청이 불가능합니다."}
```
(두 번째 성인 방송 8a933c도 동일하게 `403 / {"code":9009,"message":"미성년자는 시청이 불가능합니다."}`)

### 7-6. 성인 방송 — 대체 경로도 재생정보 없음
```
GET /service/v3.3/channels/{id}/live-detail-meta?dt=0        → 200, content.livePlaybackJson 없음
GET /service/v1/live/21769833/auto-play-info                → 200, {"livePlaybackJson":null,"previewPlaybackJson":null,...}
GET /service/v1/play-info/21769833/{id}                     → 400 {"code":400,"message":"지원하지 않는 ContentType 입니다."} (clip 전용)
GET /service/v1/channels/{id}/live-detail (=v1)             → 500 {"code":9004}
```

### 7-7. 성인 라이브 상세 응답 헤더(원본)
```
HTTP/2 200
date: Wed, 21 Oct 2026 15:12:33 GMT
content-type: application/json
access-control-allow-origin: https://chzzk.naver.com
access-control-allow-credentials: true
cache-control: no-cache, no-store, max-age=0, must-revalidate
x-frame-options: DENY
server: nfront
```

---

## 8. 막힌 원인 분석 (4단계)

| 가설 | 판정 | 근거 |
|---|---|---|
| **로그인/연령 인증 필요** | **✅ 이것이 원인** | 재생정보 요청 → `403 / code 9009 / "미성년자는 시청이 불가능합니다."`. `userAdultStatus=NOT_LOGIN_USER`. 비로그인=미성년 취급 `[확인]` |
| 지역(해외 IP) 제한 | ❌ 반증됨 | **같은 US IP**에서 일반 방송은 재생 조각까지 완전 수신. `krOnlyViewing=false`. 지역이면 일반도 막혀야 함 `[확인]` |
| 헤더/UA 문제 | ❌ 아님 | UA·Referer·Origin 없이도 일반 200. 성인 403은 헤더 무관 `[확인]` |
| 토큰/서명 오류 | ❌ 아님 | 더미 토큰(`tm=0`)으로도 일반은 playbackJson 반환. 성인만 토큰 무관 403 `[확인]` |

**원인 확정**: 치지직/네이버 API 서버가 **성인(19+) 콘텐츠의 재생 정보를, 로그인+성인(본인)인증을 마친 세션에만 발급**한다. 비로그인(해외·국내 불문)은 `9009`로 거부. 라이브 목록/상세 등 **메타데이터는 공개**이나 **재생 JSON만 연령 게이트** 뒤에 있다. 영상 CDN(akamaized) 토큰은 재생 JSON을 받아야만 생기므로 **그 앞 단계에서 원천 차단**된다.

---

## 9. 다시보기·클립 / 오픈 API 참고 (5·6단계)

- **성인 VOD(다시보기)**: `GET /service/v3/videos/{videoNo}`가 200이나, 성인 VOD는 `inKey=null, videoId=null, vodStatus=NONE, userAdultStatus=NOT_LOGIN_USER`. 재생키가 비로그인에 발급되지 않음 → 라이브와 동일한 연령 게이트 `[확인]`. 일반 VOD는 `inKey`(예 `V122f92f0529…`)·`videoId` 정상.
- **클립**: 재생정보는 `GET /service/v1/play-info/clip/{clipId}`로 받는 구조 `[추정, 번들 `Lz('clip',..)`]`. (성인 클립 재생은 라이브 결론에 추가 기여가 없어 깊이 확인하지 않음 — §11.)
- **오픈 API**(`developers.chzzk.naver.com`, 문서만 열람, 호출 안 함) `[확인, 문서]`: 카테고리는 User/Channel/Category/Live/Chat. Live 하위는 `GET /open/v1/lives`(목록, 앱 client 인증), `GET /open/v1/streams/key`(**브로드캐스터 송출키**, 유저 토큰), `GET·PATCH /open/v1/lives/setting`. **시청용 재생 URL·m3u8·VOD 재생 엔드포인트는 없음.** 성인 관련은 목록 응답의 `adult` 불리언뿐. → 공식 오픈 API로는 성인 방송 시청·녹화가 **불가능**(애초에 시청 재생 경로를 제공하지 않음).

---

## 10. 해외 IP·비로그인으로 성인 방송 녹화가 가능한가

**불가능**(이 조건에서). 성인 방송은 재생 체인의 **첫 단계(재생 정보)**에서 `403/9009`로 막히므로 마스터 m3u8·영상 조각에 도달할 수 없다. 로그인/성인인증 없이 우회할 경로는 웹 번들·공식 API 어디에도 없었다.

참고로 **일반 방송**의 재생 체인(비로그인·해외 IP로 동작 확인됨)은 다음과 같다:
1. `GET /service/v1/lives?...` 또는 채널ID로 → liveId/channelId 확보
2. `GET /service/v3.3/channels/{channelId}/live-detail` → `content.livePlaybackJson` 획득 (또는 `v1.1/.../live-playback-json-meta?tm=0`)
3. playbackJson `media[].path` = **마스터 m3u8 URL** (쿼리 `hdnts=st=…` 토큰 포함)
4. 마스터 m3u8 GET → 화질별 `hdntl=exp=<epoch>~hmac=<hmac>…/{quality}/..._hls_chunklist.m3u8`
5. 미디어(chunklist) m3u8 GET → 세그먼트(.mp4) 목록
6. 세그먼트 GET (`video/mp4`)
- 필수 헤더: `Referer: https://chzzk.naver.com/` + 데스크톱 UA(권장). **UA/Referer 없이도 200이었으나** 재테스트 환경에서는 브라우저와 동일하게 넣기를 권장.
- 토큰·만료: CDN 토큰 `hdntl`의 `exp`가 Unix epoch(관측값 `1792656379` ≈ 2026-10-22 17:06 KST, 발급 후 약 17시간). 만료 시 §2(live-detail)부터 다시 받아 재발급. **playbackAuthType=NONE**(일반)라 추가 인증 없음.

---

## 11. 확인하지 못한 것 / 다른 IP에서 재검증할 항목

1. **라이브러리 기본 UA의 치지직 반응**: 본 환경 프록시가 `python-requests/*`·`curl/*`를 치지직 도달 전에 리셋 → **일반 네트워크(한국 IP/다른 해외 망)에서 (c)·(f) 조건 재검증 필요**. (단 빈 UA·`Mozilla/5.0`은 200이므로 치지직은 UA 게이트가 없을 가능성이 큼 — `[추정]`)
2. **m3u8/세그먼트에 Referer 미설정 시 반응**: 토큰 만료로 반복 비교를 피해 미측정. CDN이 Referer를 검사하는지 재검증 필요(`[미확인]`).
3. **한국 IP에서 성인 방송**: 한국 IP라도 **비로그인이면 동일하게 9009로 막힐 것**으로 추정(게이트가 로그인 기반이므로) — 한국 IP로 직접 재확인 권장.
4. **로그인(성인인증) 세션에서의 재생 체인 전체**: 본 조사는 로그인하지 않으므로 미확인. 로그인 시 playbackJson이 나오는지, CDN 토큰·DRM(`playbackAuthType`, `com.naver.lip.smp` MediaKeySystem — 번들에서 관측)이 붙는지 재검증 필요.
5. **성인 클립** 재생(`play-info/clip/{id}`)의 비로그인 반응: 미측정(라이브 결론에 불필요).
6. **다른 CDN 유형**(`cdnInfo.cdnType`가 GCDN 외일 때)의 토큰 형식 차이: 1건만 관측.

---

## 12. 재현 방법

스크립트: `scripts/chzzk_probe.py` (부록 B에 전문). 쿠키 기능 없음. GET만. 요청 간 1.2초 간격.

필요 패키지: `pip install requests`

```bash
# 일반 방송(재생 체인 전체 확인) — 채널ID로
python3 scripts/chzzk_probe.py --channel <channelId> --segments 2 --json-out out.json

# liveId만 아는 경우(POPULAR 목록에서 채널 역조회)
python3 scripts/chzzk_probe.py --live <liveId>

# 헤더 영향 비교까지
python3 scripts/chzzk_probe.py --channel <channelId> --header-test

# 다른 IP에서 같은 시험(프록시 경유)
python3 scripts/chzzk_probe.py --channel <channelId> --proxy http://HOST:PORT

# 성인 방송 liveId로 — live-detail은 200이나 playback=False, meta는 403/9009가 찍힘
python3 scripts/chzzk_probe.py --live <adultLiveId> --no-media
```
결과 읽는 법:
- `라이브 상세 (버전별)` 블록의 `playback=True/False`가 재생정보 수신 여부.
- 성인 방송은 `live-playback-json-meta`가 `HTTP 403 ... {"code":9009,...}`로 찍힘.
- 일반 방송은 `재생 체인` 블록에서 `master → media → segment`가 모두 `HTTP 200`, 세그먼트에 `sha256`·크기 표시.
- 현재 환경(에이전트 프록시) 주의: `--header-test`의 `python-requests`/`curl 기본 UA` 조건은 프록시가 리셋할 수 있음(치지직 문제 아님). 스크립트 본 호출은 Chrome UA를 쓰므로 영향 없음.
- ※ `--header-test`는 조건마다 새 세션을 만든다. 일시적 프록시 끊김에 대비해 지수 백오프 재시도(2·4·8·16초)가 들어 있다.

---

## 13. 부록 A: 조사한 JS 번들 목록

사이트 빌드 버전(RUM_RELEASE): **`6d4fc72-20261015-104807`** (2026-10-15 빌드) `[확인]`
엔트리: `https://ssl.pstatic.net/static/nng/glive/resource/p/static/js/` 하위. (전체 메타: `evidence/bundles_meta.json`)

| 파일 | 크기(B) | SHA-256(앞16) |
|---|---|---|
| index-uNhAs37B.js (엔트리) | 5,526,594 | 79eff47113daa466 |
| rolldown-runtime-CJJwijRH.js | 1,273 | 0c0bf430afd3b71b |
| common-vendor-pcHQV1G2.js | 625,188 | 2801491c851815a1 |
| player-vendor-jlaALtVk.js | 6,638,372 | bc952e6f08baccfc |
| vendor-CwePr91W.js | 6,463,234 | 567ff0e53e98aa56 |
| date-vendor-DhkCJ9xZ.js | 845,136 | c6326ff4d567fb54 |
| worldcup_event_loading-DDING3Tt.js | 32,795 | fb1fcba9509ef2da |
| worldcup_event_result_win-vBR6lPpU.js | 101,146 | 69ef610494c28203 |
| worldcup_event_result_lose-BFT13MGt.js | 86,316 | 287bbefe9abe4957 |
| clipEditor-C4hIb_wR.js | 44,177 | 5d5366c32911721c |
| strings-ko_kr-LkHMJrFd.js | 335,298 | 7174eaa68be4b714 |
| strings-en_us-CFTz6Ot7.js | 149,748 | 868ef7bf46c46dc9 |
| strings-vi_vn-DLL2AQnC.js | 149,689 | 18d97819144857c8 |
| desktop-media-viewer.min.js | 397,330 | 4edd36b3a16d9a3e |
| refresh-detector-obfuscated.js | 2,717 | 9a894d5316aee53a |
| media-capable-log.js | 4,162 | e9b9d7c98f625a49 |

번들에서 추출한 **전체 API 호출 지점 303개** 목록은 `evidence/api_calls_from_bundle.json`. (성인 관련 분기: `adult`/`userAdultStatus`/`NOT_LOGIN_USER`는 응답 필드이며, 번들은 이 값으로 로그인·성인인증 유도 UI를 분기한다 `[확인, 번들]`.)

재생 경로 관련 번들 함수(원본 식별자):
- `em(e,t) = Np(ys, /channels/{e}/live-detail-meta?dt={t})` — v3.3 터널링
- `nm(e) = Np(hs, /channels/{e}/live-playback-json-meta?tm={Qp()})` — v1.1 터널링, `Qp()`는 `com.naver.lip.smp` MediaKeySystemAccess 확인값
- `Np` = 터널링 클라이언트(`Ep()`가 PEM 공개키·whitelist로 초기화) — DRM/안티봇 계층 `[추정]`. 단 더미 토큰으로도 일반 콘텐츠는 응답됨(§4).

---

## 14. 부록 B: 재현 스크립트 전문 (`scripts/chzzk_probe.py`)

```python
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

```

