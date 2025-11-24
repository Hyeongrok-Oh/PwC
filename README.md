# 한경 컨센서스 애널리스트 리포트 분석 프로젝트

LG전자 및 삼성전자 TV 산업 관련 리포트에서 KPI-요인 관계를 추출하는 파이프라인

## 설치 방법

```bash
pip install -r requirements.txt
```

## 사용 방법

### Step 1: 데이터 수집

#### Step 1: 한경 컨센서스 애널리스트 리포트 크롤링 ✅

```bash
python 01_crawl_consensus.py
# 또는 Windows에서
run_01_consensus.bat
```

LG전자, 삼성전자의 최근 1년간 애널리스트 리포트를 수집합니다.

#### Step 2: DART 사업보고서 메타데이터 수집 ✅

```bash
python 02_crawl_dart_metadata.py
# 또는 Windows에서
run_02_dart_metadata.bat
```

LG전자, 삼성전자의 다음 보고서 메타데이터를 수집합니다:
- 사업보고서 (연간)
- 반기보고서
- 분기보고서

#### Step 3: DART 원문 공시 문서 다운로드 ✅

```bash
python 03_download_dart_documents.py
# 또는 Windows에서
run_03_dart_documents.bat
```

DART 메타데이터(Step 2)에서 접수번호를 읽어 원문 공시 문서(ZIP)를 다운로드합니다.

#### Step 4: 텍스트 추출 ✅

```bash
python 04_extract_text.py
# 또는 Windows에서
run_04_extract_text.bat
```

PDF와 XML 파일에서 텍스트를 추출하여 JSON 형식으로 저장합니다.

#### Step 5: TV 관련 리포트 필터링 ✅

```bash
python 05_filter_tv_reports.py
# 또는 Windows에서
run_05_filter.bat
```

추출된 텍스트에서 TV 관련 키워드(TV, OLED, 디스플레이, 패널 등)를 포함하는 리포트만 필터링합니다.
- 총 79개 문서 중 62개 TV 관련 문서 필터링 (78.5%)
- 필터링된 결과는 `data/filtered/filtered_index.json`에 저장됩니다

#### Step 5.5: Consensus TV 문단 추출 (비용 최적화) ✅

```bash
python 06_extract_tv_content.py
# 또는 Windows에서
run_06_extract_tv_content.bat
```

Consensus 문서에서 TV 관련 키워드가 포함된 문단만 추출하여 LLM API 비용을 절감합니다.
- 54개 Consensus 문서 처리
- 67.5% 데이터 감소 (614,161자 → 199,609자)
- LG전자: 74.4% 감소, 삼성전자: 63.3% 감소
- 622K 토큰 절감 (한글 1.5배 환산)
- 예상 비용 절감: GPT-4 $18.65, Claude 3.5 Sonnet $1.87, Gemini Flash 2.5 $0.047
- 추출된 결과는 `data/filtered/tv_content/consensus/`에 저장됩니다

## 프로젝트 구조

```
PwC/
├── config.py                      # 설정 파일
├── 01_crawl_consensus.py          # Step 1: 한경 컨센서스 크롤링
├── 02_crawl_dart_metadata.py      # Step 2: DART 메타데이터 수집
├── 03_download_dart_documents.py  # Step 3: DART 문서 다운로드
├── 04_extract_text.py             # Step 4: 텍스트 추출
├── 05_filter_tv_reports.py        # Step 5: TV 관련 필터링
├── 06_extract_tv_content.py       # Step 5.5: Consensus TV 문단 추출
├── setup_venv.bat                 # 가상환경 설정
├── run_01_consensus.bat           # Step 1 실행
├── run_02_dart_metadata.bat       # Step 2 실행
├── run_03_dart_documents.bat      # Step 3 실행
├── run_04_extract_text.bat        # Step 4 실행
├── run_05_filter.bat              # Step 5 실행
├── run_06_extract_tv_content.bat  # Step 5.5 실행
├── .gitignore                     # Git 제외 파일
├── .env.example                   # 환경변수 예시
├── data/                          # 데이터 폴더 (Git에서 제외됨)
│   ├── raw/
│   │   ├── consensus/            # 한경 컨센서스 PDF 파일
│   │   ├── dart/                 # DART 원문 공시 ZIP 파일
│   │   └── *.json                # 메타데이터 파일
│   ├── extracted/                # 추출된 텍스트
│   │   ├── consensus/            # PDF 텍스트 (JSON)
│   │   ├── dart/                 # XML 텍스트 (JSON)
│   │   └── index.json            # 통합 인덱스
│   ├── filtered/                 # TV 관련 필터링 결과
│   │   ├── filtered_index.json   # 필터링된 문서 인덱스 (62개)
│   │   └── tv_content/           # TV 문단만 추출 (비용 최적화)
│   │       ├── consensus/        # Consensus TV 문단 (54개)
│   │       └── tv_content_index.json  # TV 문단 인덱스
│   └── processed/                # KPI-요인 추출 결과 (예정)
├── requirements.txt
├── README.md
├── DATA_SUMMARY.md
├── PROJECT_STRUCTURE.md
└── QUICKSTART.md
```

## 처리 단계

### ✅ Step 1-3: 데이터 수집
- **한경 컨센서스**: LG전자, 삼성전자 애널리스트 리포트 수집 (최근 1년)
  - 메타데이터(JSON) + PDF 파일 (71개)
- **DART API**: 사업보고서, 반기보고서, 분기보고서 수집 (최근 1년)
  - 메타데이터(JSON) + 원문 공시 문서(ZIP/XML) (8개)

### ✅ Step 4: 텍스트 추출
- PDF 텍스트 추출 (pdfplumber)
- XML 텍스트 추출 (lxml)
- 총 79개 문서에서 텍스트 추출 완료

### ✅ Step 5: TV 관련 리포트 필터링
- TV 관련 키워드 기반 필터링 (TV, OLED, 디스플레이, 패널, UHD 등)
- 총 79개 문서 중 62개 TV 관련 문서 필터링 (78.5%)
  - Consensus: 54/71개 (76.1%) - 전체 문서 필터링
  - DART: 8/8개 (100%) - TV 관련 문단 추출
  - LG전자: 30개 (100%), 삼성전자: 32개 (65.3%)
- DART 문서는 TV 관련 문단과 주변 문맥만 추출하여 저장

### ✅ Step 5.5: Consensus TV 문단 추출 (비용 최적화)
- Consensus 문서에서 TV 관련 키워드가 포함된 문단만 추출
- 54개 Consensus 문서에서 67.5% 데이터 감소
  - 원본: 614,161자 → TV 문단: 199,609자
  - LG전자: 74.4% 감소 (231,394자 → 59,258자)
  - 삼성전자: 63.3% 감소 (382,767자 → 140,351자)
- 622K 토큰 절감으로 LLM API 비용 대폭 절감
  - GPT-4: $18.65 절감
  - Claude 3.5 Sonnet: $1.87 절감
  - Gemini Flash 2.5: $0.047 절감

### Step 6: KPI-요인 추출 (예정)
- LLM을 활용한 구조화된 정보 추출
- Graph Database 노드/엣지 생성

## 주의사항

### 한경 컨센서스 크롤러
1. 첫 실행 시 ChromeDriver가 자동으로 다운로드됩니다
2. 사이트 구조가 변경되면 `crawler.py`의 CSS selector를 수정해야 할 수 있습니다
3. 크롤링 속도 제한을 위해 딜레이가 설정되어 있습니다

### DART API 크롤러
1. DART API 인증키가 `config.py`에 포함되어 있습니다
2. API 요청 제한: 분당 1,000건, 일일 10,000건
3. 인터넷 연결이 필요합니다

## 수집 결과

### 한경 컨센서스
- LG전자: 23개 리포트 (메타데이터 + PDF)
- 삼성전자: 45개 리포트 (메타데이터 + PDF)

### DART API
- LG전자: 4개 보고서 (사업보고서 1개, 반기보고서 1개, 분기보고서 2개)
  - 메타데이터 + 원문 공시 문서(ZIP/XML)
- 삼성전자: 4개 보고서 (사업보고서 1개, 반기보고서 1개, 분기보고서 2개)
  - 메타데이터 + 원문 공시 문서(ZIP/XML)
