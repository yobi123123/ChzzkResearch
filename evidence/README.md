# evidence/

보고서(`report/CHZZK_API_전수조사_해외IP_20261021.md`)의 판단 근거가 된 원본 응답 일부와 메모. 보고서만으로 결론·재현이 가능하며, 여기는 원본 보관용이다. CDN 토큰 값(hdnts/hdntl/hmac)은 앞 8자만 남기고 마스킹했다. 받은 영상 조각(.mp4)은 올리지 않았다(크기·SHA-256만 보고서 §6에 기록).

- `api_calls_from_bundle.json` — 1단계 정적분석: 번들에서 추출한 API 호출 지점 303개(메서드/베이스/경로).
- `bundles_meta.json` — 조사한 JS 번들 16개의 URL·크기·SHA-256(부록 A).
- `normal_ralo.json` — 일반 방송(랄로) 프로브 전체 결과: 라이브상세 버전별 → 마스터/미디어 m3u8 → 세그먼트(상태·크기·sha256).
- `live-detail_v3.3_normal_ralo.json` — 일반 방송 live-detail v3.3 원본(livePlaybackJson 포함, 토큰 마스킹).
- `adult_feb20a.json`, `adult_8a933c.json` — 성인 방송 2건 프로브 결과(live-playback-json-meta가 403/9009).
- `live-detail_v3.3_adult.json` — 성인 방송 live-detail v3.3 원본(adult=true, userAdultStatus=NOT_LOGIN_USER, livePlaybackJson=null).
- `raw_adult_live-detail_headers.txt` — 성인 live-detail 응답 헤더 원본(server: nfront, CORS 등).
