# B3-2 작업 규칙

- 작업 시작 전에 WORK_LOG.md를 읽고, 종료 전에 날짜/시간·요청·변경 파일·검증 결과·미해결·다음 작업을 이어서 기록한다.
- 비밀번호·API 키·환경변수 실제 값은 코드·로그·문서에 저장하지 않는다.
- 미션 원문은 docs/mission-requirements.txt이며 원본을 보존한다.
- CLI는 Git status/diff 조회와 초안 출력만 한다. 자동 commit/push/PR 생성 기능을 넣지 않는다.
- B3-1의 파일과 AWS 리소스는 수정하지 않는다.
- 실제 API 결과와 테스트 대역/문서 예시를 구분하고, 한국어로 설명한다.
- 테스트: python3.12 -m unittest discover -s tests -v
