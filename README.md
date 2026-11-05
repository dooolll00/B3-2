# B3-2 · AI Git 커밋/PR 초안 생성기

Git 변경 내용을 읽어 AI로 **변경 요약·커밋 메시지·PR 제목과 본문**을 만드는 Python CLI입니다. 출력한 초안은 검토 후 복사해 사용합니다.

현재 로컬 구현과 자동 테스트 22개가 통과했습니다. 실제 OpenAI API 호출과 GitHub 업로드는 아직 완료하지 않았습니다. 테스트 대역과 아래 설명용 예시는 실제 AI 실행 증빙이 아닙니다. [요구사항별 진행 상태](docs/verification.md)

## 설치

Python **3.10 이상**, Git, 인터넷 연결이 필요합니다. 외부 Python 패키지는 사용하지 않습니다.

```bash
cd /Users/dooolll5969/Desktop/B3-2
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python main.py --help
```

이 Mac의 기본 `python3`은 3.9이므로 `python3.12`를 사용합니다. 다른 환경에서는 3.10 이상인 Python 실행 파일을 선택하세요. `.venv` 활성화 후의 `python`은 그 버전을 사용합니다.

## API 키 설정

OpenAI API 키는 환경변수 `AI_API_KEY`로만 받습니다. `OPENAI_API_KEY`도 대체 이름으로 지원하며 둘 다 있으면 `AI_API_KEY`를 우선합니다. `.env` 파일은 읽지 않습니다.

macOS 기본 zsh에서 아래 명령은 입력한 키를 화면과 명령 기록에 남기지 않고 현재 터미널에 설정합니다.

```zsh
read -s "AI_API_KEY?OpenAI API Key: "
export AI_API_KEY
printf '\n'
```

API 키를 코드·README·작업 기록·스크린샷에 넣지 마세요. API 사용 가능 모델과 잔액은 계정별로 확인해야 합니다. 작업을 마치면 `unset AI_API_KEY`로 현재 셸에서 해제할 수 있습니다.

## Git 변경 준비와 전송 미리보기

대상 Git 저장소 **루트**에서 실행합니다. 도구를 다른 저장소에 적용할 때는 그 저장소로 이동한 뒤 `python /경로/B3-2/main.py commit`처럼 실행하세요.

```bash
# 이 프로젝트를 처음 검증할 때: 필요한 소스와 문서를 검토한 뒤 스테이징
# git add는 사용자가 직접 수행하며 CLI에서는 실행하지 않습니다.
git add main.py README.md AGENTS.md WORK_LOG.md .gitignore docs tests
python main.py all --preview
```

- `git status --porcelain=v1 -z`로 파일과 상태를 읽습니다.
- `git diff`와 `git diff --cached`를 각각 읽어 미스테이징·스테이징 변경을 함께 전달합니다.
- 미추적 파일은 이름만 포함합니다. **새 파일의 내용까지 요약하려면 먼저 `git add 파일명`으로 스테이징하세요.**
- 변경이 없으면 키 없이도 정상 종료하며 API 요청은 0회입니다.
- `--preview`는 실제 전송할 JSON을 출력하고 종료합니다. API 요청은 0회입니다.
- 병합 충돌은 먼저 해결하도록 안내합니다. 바이너리 파일은 Git diff의 변경 표시만 전달하며 내용을 분석하지 않습니다.
- PR도 현재 작업 트리와 스테이징 변경을 요약합니다. 이미 커밋한 브랜치 전체나 원격 브랜치와의 차이는 수집하지 않습니다.

## 실행

```bash
# 커밋 초안
python main.py commit --reason '잘못된 입력을 조기에 차단하기 위해'

# PR 초안
python main.py pr --requirements 'Why/What/How to Test를 한국어로 작성'

# 한 번의 실행과 보통 1회 API 호출로 커밋과 PR을 함께 생성
python main.py all --max-tokens 2500

# 모델과 생성 파라미터 변경
python main.py commit --model gpt-4.1-mini --temperature 0.2 --max-tokens 1500

# 팀 표현 규칙과 전송 범위 변경
python main.py pr --convention 'docs/fix/feat prefix, 한국어, 과장 금지' --max-files 5 --max-lines 120
```

기본 모델은 `gpt-4.1-mini`입니다. 다른 모델을 지정할 때는 Chat Completions·JSON object·temperature 파라미터 지원 여부를 확인하세요. 지원하지 않는 조합은 API 요청 오류로 안내합니다.

| 옵션 | 기본값 | 의미 |
|---|---|---|
| 명령 | 필수 | `commit`, `pr`, `all` |
| `--model` | `gpt-4.1-mini` | 요청 모델 |
| `--temperature` | `0.2` | 0~2, 낮을수록 표현 변동을 줄이는 방향. 사실 정확성을 보장하지 않음 |
| `--max-tokens` | `1500` | API의 `max_completion_tokens`로 보내는 최대 출력 토큰 수. 글자 수와 다름 |
| `--safe-mode` | ON | 패턴 마스킹과 파일·줄 제한 |
| `--no-safe-mode` | 미사용 | 패턴 마스킹·파일·줄 제한 해제. 민감 파일 제외와 환경변수 API 키 제거는 유지 |
| `--max-files` | `10` | 안전 모드에서 전송할 최대 파일 수 |
| `--max-lines` | `200` | 안전 모드에서 파일별 diff를 합친 최대 줄 수(안내 표식 제외) |
| `--reason` | 빈 값 | 변경 배경. 없으면 AI에 확인 필요로 표현하도록 지시 |
| `--requirements` | 빈 값 | 요구사항 맥락 |
| `--convention` | 한국어·Conventional Commits | 팀 표현 규칙을 프롬프트에 추가 |
| `--preview` | 미사용 | 입력만 출력, 실제 API 호출 없음 |

`-model`, `-temperature`, `-max-tokens`, `-safe-mode` 별칭도 지원합니다. 모든 옵션은 명령 뒤에 넣으세요.

## 출력 예시

아래는 **형식 설명용 예시이며 실제 API 실행 결과가 아닙니다.**

```text
[INFO] 변경 1개, 전송 1개, 민감 파일 제외 0개, 제한으로 생략 0개
[INFO] 안전 모드: ON
[INFO] AI API 요청 횟수: 1

--- Change Summary ---
입력 검증을 추가합니다.

--- Commit Message ---
feat: CLI 입력 검증 추가

- 잘못된 옵션 입력을 거부하고 오류를 안내

--- PR Title ---
feat: CLI 입력 검증 추가

--- PR Body ---

## Why
- 잘못된 입력으로 API가 호출되는 것을 방지하기 위해

## What
- CLI 옵션 범위 검증과 오류 메시지 추가

## How to Test
- 잘못된 temperature로 실행해 오류와 종료 코드 확인
```

실제 명령은 출력 끝에 직접 검토·적용 안내도 표시합니다. `commit`은 커밋만, `pr`은 PR만, `all`은 둘 다 출력합니다.

## 요청과 검증 흐름

`Git status/diff → 제외·마스킹·크기 제한 → 맥락과 JSON 출력 규칙 추가 → HTTPS REST 요청 → 응답 JSON 해석 → 형식 검증 → 터미널 출력`

- Python `subprocess.run`에 인자 배열을 전달하고 셸 명령 문자열을 실행하지 않습니다. Git 외부 diff·textconv도 끕니다.
- Python `urllib.request`로 OpenAI Chat Completions에 JSON POST를 보냅니다. 인증 키는 Authorization 헤더에만 사용합니다.
- 시스템 프롬프트에 출력 규칙을, 사용자 JSON에 diff와 배경·요구사항·컨벤션을 넣습니다. diff 속 지시는 신뢰하지 않도록 분리합니다.
- 커밋 제목은 한 줄·최대 72자, 50자를 넘으면 권장 길이 안내를 표시합니다. 본문이 있으면 변경 불릿을 요구합니다.
- PR 제목은 한 줄·최대 80자입니다. Why/What/How to Test 배열이 각각 비어 있지 않은지 검증한 뒤 프로그램이 헤더와 불릿을 붙입니다.
- 형식이 틀리면 최대 1회 재생성합니다. **명령당 최대 2회**이며 자동 네트워크 재시도는 없습니다. `all`도 최대 2회입니다.
- 형식 검증은 사실 검증이 아닙니다. 변경 이유·테스트 실행 여부·생략된 변경은 사람이 검토해야 합니다.
- CLI는 commit·push·GitHub PR 생성·파일 수정 기능을 제공하지 않습니다. 출력 텍스트를 적용하는 작업은 사용자가 직접 합니다.

## 민감정보와 비용

기본 안전 모드는 `.env`, `.env.*`, 개인키 확장자, `.aws`/`.ssh` 하위 파일, credentials 파일 등을 제외합니다. 이메일, OpenAI/GitHub/AWS 키 패턴, password/token 등의 대입 값, PEM 개인키 블록을 마스킹합니다. 파일명과 사용자 입력 맥락에도 마스킹을 적용합니다.

패턴 검사는 모든 개인정보·비밀값을 찾아내지 못합니다. `--preview`로 전송 내용을 확인하고 조직의 전송 정책을 따르세요. 안전 모드 OFF 미리보기에는 민감정보가 표시될 수 있어 공유하면 안 됩니다. API 키의 실제 환경변수 값은 두 모드 모두 전송 맥락에서 제거합니다.

기본 제한은 최대 **10개 파일·200줄**이며 모드와 관계없이 전체 입력 JSON **60,000자**를 넘으면 호출하지 않습니다. API 연결 제한은 45초입니다. 이는 금액 상한이 아니므로 계정 사용량도 확인하세요. 출력 토큰 한도에 도달하면 `--max-tokens`를 조정해 직접 다시 실행합니다. `store: false`는 생성 결과 저장 옵션이며 전체 데이터 보관 정책을 대체하지 않습니다.

## 오류 대응

| 메시지/상황 | 대응 |
|---|---|
| 변경 사항이 없습니다 | 정상 종료(0), 변경을 만든 뒤 실행 |
| 미추적 파일 내용 미수집 | 필요한 파일을 `git add` 후 실행 |
| API 키 미설정 | 같은 터미널에서 환경변수 설정 |
| HTTP 400 | 모델·파라미터 지원 조합 확인 |
| HTTP 401 / 403 / 404 | 각각 인증 / 권한 / 모델 이름·사용 가능 여부 확인 |
| HTTP 429 | 잔액·요청 제한 확인 |
| 네트워크/연결 오류 | 인터넷·DNS·TLS·시간 제한 확인 |
| 형식 검증 2회 실패 | 모델·토큰 수·컨벤션을 조정한 뒤 실행 |
| 입력 60,000자 초과 | `--max-files`, `--max-lines` 축소 |

오류는 종료 코드 1, 사용자 중단은 130입니다. API 오류 원문은 입력을 반사해 민감정보를 노출할 수 있어 출력하지 않고 HTTP 코드별 원인 안내를 표시합니다.

## 테스트와 제출

```bash
python -m unittest discover -s tests -v
```

테스트는 임시 Git 저장소와 가짜 API 응답을 사용하며 실제 요청 비용이 발생하지 않습니다. [검증 결과와 남은 작업](docs/verification.md)을 참고하세요.

실제 API 검증은 변경을 준비하고 `--preview` 확인 후 `python main.py all --max-tokens 2500`을 실행합니다. 키를 제외한 명령·출력·실행 시각·호출 횟수를 보관하세요.

GitHub 저장소는 사용자가 새로 만들 예정입니다. 생성할 때 README·라이선스·gitignore 없이 빈 저장소를 만들면 충돌을 줄일 수 있습니다. 원격 주소를 받은 뒤 인증 가능한 터미널에서 다음 흐름으로 진행합니다(아직 실행하지 않음).

```bash
git add main.py README.md AGENTS.md WORK_LOG.md .gitignore docs tests
git commit -m "feat: add AI Git draft generator"
git remote add origin <새로_만든_GitHub_저장소_URL>
git push -u origin main
```

초안 생성은 커밋 전에 수행하세요. 브랜치 작업 흐름은 다음 의미 있는 개선을 `git switch -c feature/개선이름`에서 진행하며 남깁니다. 실제 업로드 주소와 커밋·브랜치 증빙은 완료 후 추가합니다.

선택 보너스 중 `--convention`과 조정 가능한 안전 모드 기능은 구현했지만, 이전 미션의 팀 스타일 분석·비교 생성 결과와 실제 PR 증빙은 아직 없습니다.

## 파일

```text
main.py                         CLI, Git 수집, 안전 모드, REST 연동, 출력 검증
tests/test_main.py              Git 및 API 성공/실패 자동 테스트
docs/mission-requirements.txt   사용자 제공 미션 원문
docs/verification.md            요구사항별 검증·미완료 항목
WORK_LOG.md                    이어서 작업하기 위한 기록
AGENTS.md                      이 프로젝트 작업 규칙
```

공식 참고: [Chat Completions 요청 파라미터](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
