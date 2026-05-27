# 설치 및 사용 가이드 — Altiplano Resiliente

> 이 가이드는 코딩을 모르는 직원이 자신의 컴퓨터에서
> 지도 업데이트 웹 도구를 설치하고 사용할 수 있도록 작성되었습니다.

---

## 사전 요구사항

시작하기 전에 다음이 필요합니다:

| 요구사항 | 세부사항 |
|:---------|:---------|
| Windows 10 또는 11 | Windows에서만 동작합니다 |
| Python 3.10 이상 | https://www.python.org/downloads/ 에서 다운로드 |
| ArcGIS Pro | 파이프라인 3, 4단계에 필요 |
| 인터넷 연결 | 패키지 다운로드 및 Smartsheet 연결용 |
| 공유 인증정보 | Smartsheet 토큰, 시트 ID, ArcGIS Online 인증정보 |

### Python 설치 여부 확인 방법

1. `Win + R`을 누르고 `cmd`를 입력한 후 Enter
2. `python --version`을 입력하고 Enter
3. `Python 3.12.x` 같은 메시지가 나오면 설치 완료 상태
4. 명령어를 인식하지 못하면 Python 설치가 필요

### Python 설치 (없는 경우)

1. https://www.python.org/downloads/ 접속
2. 최신 버전 다운로드 (큰 노란색 버튼)
3. **중요**: 설치 프로그램 하단의 **"Add Python to PATH"** 체크박스를 반드시 선택
4. "Install Now" 클릭
5. 완료될 때까지 기다린 후 설치 프로그램 종료

---

## 1단계: 프로그램 받기

### 방법 A — ZIP으로 다운로드 (더 간단함)

1. GitHub의 프로젝트 저장소로 이동
2. 녹색 **"Code"** 버튼 클릭
3. **"Download ZIP"** 선택
4. 원하는 폴더에 압축 해제 (예: `C:\AR\altiplano`)

### 방법 B — Git으로 클론 (Git이 설치된 경우)

```
git clone https://github.com/yunyongs/altiplano.git
```

---

## 2단계: 자동 설치 프로그램 실행

1. 프로젝트를 압축 해제하거나 클론한 폴더를 엽니다
2. **`setup.bat`** 파일을 **더블클릭**합니다
3. 설치 프로그램이 자동으로 다음을 수행합니다:
   - Python 설치 확인
   - 가상 환경 생성 (`.venv` 폴더)
   - 필요한 패키지 설치
   - 컴퓨터의 ArcGIS Pro 감지
4. **처음 실행하는 경우**, 팀 공유 인증정보를 입력하라는 메시지가 표시됩니다:

| 요청 데이터 | 설명 | 제공자 |
|:------------|:-----|:-------|
| Smartsheet API Token | Smartsheet 접근 키 | 팀 관리자 |
| Sheet ID - C1 | 컴포넌트 1 시트 식별자 | 팀 관리자 |
| Sheet ID - C2 | 컴포넌트 2 시트 식별자 (선택) | 팀 관리자 |
| Sheet ID - C3 | 컴포넌트 3 시트 식별자 (선택) | 팀 관리자 |
| ArcGIS Client ID | ArcGIS Online 인증정보 | 팀 관리자 |
| ArcGIS Client Secret | ArcGIS Online 인증정보 | 팀 관리자 |

5. 완료되면 **"설치 완료!"** 메시지가 표시됩니다

> **참고:** 이전 설치의 `.env` 파일이 이미 있는 경우, 설치 프로그램은
> 인증정보를 건드리지 않고 ArcGIS Pro 정보만 업데이트합니다.

---

## 3단계: 애플리케이션 시작

1. **`run.bat`** 파일을 **더블클릭**합니다
2. 검은 창(터미널)이 열리며 다음 메시지가 표시됩니다:
   ```
   서버 주소: http://localhost:5000
   ```
3. 웹 브라우저를 엽니다 (Chrome, Edge, Firefox)
4. 주소창에 **http://localhost:5000** 을 입력합니다
5. Altiplano Resiliente 대시보드가 표시됩니다

> **중요:** 애플리케이션을 사용하는 동안 검은 창을 닫지 마세요.
> 닫으면 서버가 중지되고 웹 페이지가 작동하지 않습니다.

---

## 4단계: 로컬 경로 설정

애플리케이션을 처음 열면 컴퓨터의 로컬 폴더 경로를 설정해야 합니다:

1. 왼쪽 사이드바에서 **"Rutas Locales"** 클릭
2. 해당 PC에 맞는 경로를 입력합니다:

| 필드 | 설명 | 예시 |
|:-----|:-----|:-----|
| FOLDER_C1 | 컴포넌트 1 다운로드 폴더 | `C:\Users\사용자\OneDrive\AR\C1` |
| FOLDER_C2 | 컴포넌트 2 다운로드 폴더 | `C:\Users\사용자\OneDrive\AR\C2` |
| FOLDER_C3 | 컴포넌트 3 다운로드 폴더 | `C:\Users\사용자\OneDrive\AR\C3` |
| GDB_PATH | ArcGIS 지오데이터베이스 경로 | `C:\Users\사용자\Documents\AR\AR.gdb` |
| WORKSPACE_PATH | ArcGIS Pro 작업 폴더 | `C:\Users\사용자\Documents\ArcGIS\Projects\AR` |
| APRX | ArcGIS Pro 프로젝트 파일 경로 | `C:\...\AR\AR.aprx` |

3. **"Guardar"** (저장) 클릭

> 이 경로는 각 컴퓨터마다 다르며 팀과 공유되지 않습니다.

---

## 일상 사용법

### 애플리케이션 열기

1. **`run.bat`** 더블클릭
2. 브라우저에서 **http://localhost:5000** 접속

### 애플리케이션 종료

1. 검은 창(터미널)으로 이동
2. **Ctrl + C** 누르기
3. 창 닫기

### 작업 흐름 (7단계)

애플리케이션이 7단계로 업데이트 과정을 안내합니다:

| 단계 | 기능 | 방법 |
|:----:|:-----|:-----|
| 1 | Smartsheet에서 데이터 다운로드 | 자동 — 1단계 버튼 클릭 |
| 2 | Smartsheet와 GIS 데이터 비교 | 자동 — "교차 검증 실행" 클릭 |
| 3 | ArcGIS Pro용 스크립트 생성 | 스크립트를 복사하여 ArcGIS Pro에 붙여넣기 |
| 4 | ArcGIS Online에 데이터 게시 | 스크립트를 복사하여 ArcGIS Pro에 붙여넣기 |
| 5 | 마스터 Excel 파일 생성 | 자동 |
| 6 | Power BI 대시보드 업데이트 | 스크립트를 복사하여 실행 |
| 7 | 보고서 생성 및 백업 | 자동 |

---

## 문제 해결

### "Python을 인식할 수 없습니다"
- Python이 설치되지 않았거나 PATH에 추가되지 않음
- **"Add Python to PATH"** 체크박스를 선택하고 Python 재설치

### ".venv를 찾을 수 없습니다"
- `run.bat` 전에 `setup.bat`을 먼저 실행하세요

### ".env 파일이 없습니다"
- `setup.bat`을 실행하여 설정 파일을 생성하세요

### 브라우저에서 페이지가 로드되지 않음
- 검은 창이 열려 있고 "Running on http://localhost:5000" 메시지가 있는지 확인
- 브라우저를 닫고 다시 열어보세요
- 다른 프로그램이 5000번 포트를 사용하고 있지 않은지 확인

### ArcGIS Pro가 감지되지 않음
- ArcGIS Pro가 설치되어 있는지 확인
- ArcGIS Pro 설치 후 `setup.bat`을 다시 실행

### ArcPy 스크립트가 작동하지 않음
- ArcGIS Pro의 **Python** 창에 붙여넣기 (Notebook이 아님)
- "Rutas Locales"에서 로컬 경로가 올바르게 설정되어 있는지 확인

### "Path outside allowed directories" 오류

- "로컬 경로"에서 설정된 경로가 허용된 디렉토리를 정의합니다
- 다운로드 및 백업 폴더가 설정된 경로 내에 있는지 확인하세요
- 다른 폴더를 사용해야 하는 경우, 먼저 로컬 경로 설정에 추가하세요

### ZIP 파일 추출 오류

- 시스템은 ZIP 파일을 추출하기 전에 안전성을 검증합니다
- "ZIP member escapes target directory" 메시지가 표시되면 ZIP 파일이 손상되었을 수 있습니다
- 보고자에게 ZIP 파일을 다시 보내달라고 요청하세요

---

## 고급 설정

### 환경 변수 `FLASK_DEBUG`

기본적으로 디버그 모드는 **비활성화**되어 있습니다. 문제 진단을 위해 디버그 모드를
활성화해야 하는 경우 (개발용으로만 사용):

1. 텍스트 편집기로 `.env` 파일을 엽니다
2. 다음 줄을 추가합니다: `FLASK_DEBUG=1`
3. 애플리케이션을 재시작합니다 (`run.bat`을 닫고 다시 엽니다)

> **중요:** 일반 사용 시에는 `FLASK_DEBUG=1`을 활성화된 상태로 두지 마세요.
> 디버그 모드는 일상적인 사용에 필요하지 않은 상세한 기술 정보를 표시합니다.

---

## 주요 파일 구조

```
altiplano/
|
|-- setup.bat          <-- 한 번만 실행 (설치용)
|-- run.bat            <-- 매번 실행 (앱 시작용)
|-- .env               <-- 인증정보 및 설정 (공유 금지)
|
|-- app.py             <-- 서버 (수정하지 마세요)
|-- templates/         <-- 웹 인터페이스 (수정하지 마세요)
|-- static/            <-- 웹 스타일 및 스크립트 (수정하지 마세요)
```

> **중요 규칙:** 프로그램 파일을 수정하지 마세요.
> 모든 설정은 `setup.bat`과 웹 인터페이스를 통해 수행됩니다.

---

## 연락처 및 지원

설치나 사용에 문제가 있으면 인증정보를 제공한 팀 관리자에게 문의하세요.
