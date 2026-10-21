# soop/evidence/

SOOP 조사(`soop/report/SOOP_API_전수조사_해외IP_20261021.md`) 근거 원본. AID·FTK 등 토큰은 앞 8자만 남기고 마스킹. 영상 조각(.TS)은 올리지 않음(크기·SHA-256만 보고서 §4에 기록).

- `recon_http_log.jsonl` — 조사 중 전체 HTTP 호출 로그(94건, 토큰 마스킹).
- `probe_normal_live.json` — 일반 라이브 프로브 결과(재생정보→마스터→미디어→조각, 전 단계 200).
- `probe_성인.json` / `probe_비번.json` / `probe_구독.json` — 형태별 게이트 결과(RESULT -6 / BPWD=Y·aid 0 / -14).
- `sample_channel_normal.json` — 일반 라이브 player_live_api 전체 CHANNEL 응답(토큰 마스킹).
