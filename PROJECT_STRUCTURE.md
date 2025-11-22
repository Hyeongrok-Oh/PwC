# 프로젝트 구조

## Python 스크립트 (실행 순서)

### 1️⃣ 01_crawl_consensus.py
**기능**: 한경 컨센서스 애널리스트 리포트 크롤링
- **입력**: 없음 (config.py에서 설정 읽기)
- **출력**:
  - `data/raw/LG전자_YYYYMMDD_HHMMSS.json` - 메타데이터
  - `data/raw/삼성전자_YYYYMMDD_HHMMSS.json` - 메타데이터
  - `data/raw/consensus/*.pdf` - PDF 파일 (71개)
- **실행**: `run_01_consensus.bat` 또는 `python 01_crawl_consensus.py`

### 2️⃣ 02_crawl_dart_metadata.py
**기능**: DART 사업보고서 메타데이터 수집
- **입력**: 없음 (API를 통해 수집)
- **출력**:
  - `data/raw/LG전자_DART_YYYYMMDD_HHMMSS.json`
  - `data/raw/삼성전자_DART_YYYYMMDD_HHMMSS.json`
- **실행**: `run_02_dart_metadata.bat` 또는 `python 02_crawl_dart_metadata.py`

### 3️⃣ 03_download_dart_documents.py
**기능**: DART 원문 공시 문서 다운로드
- **입력**: Step 2에서 생성된 메타데이터 JSON 파일
- **출력**:
  - `data/raw/dart/*.zip` - 원문 공시 ZIP 파일 (8개)
- **실행**: `run_03_dart_documents.bat` 또는 `python 03_download_dart_documents.py`

## 데이터 구조

```
data/
└── raw/
    ├── consensus/                        # 한경 컨센서스 PDF
    │   ├── LG전자_*.pdf (26개)
    │   └── 삼성전자_*.pdf (45개)
    │
    ├── dart/                             # DART 원문 공시
    │   ├── LG전자_*_사업보고서.zip
    │   ├── LG전자_*_반기보고서.zip
    │   ├── LG전자_*_분기보고서.zip (2개)
    │   ├── 삼성전자_*_사업보고서.zip
    │   ├── 삼성전자_*_반기보고서.zip
    │   └── 삼성전자_*_분기보고서.zip (2개)
    │
    └── 메타데이터 JSON 파일:
        ├── LG전자_20251121_213526.json          (한경 컨센서스)
        ├── 삼성전자_20251121_221702.json        (한경 컨센서스)
        ├── LG전자_DART_20251122_011004.json     (DART)
        └── 삼성전자_DART_20251122_011005.json   (DART)
```

## 설정 파일

### config.py
- `COMPANIES`: 대상 회사 및 종목코드
- `CONSENSUS_DIR`: 한경 컨센서스 PDF 저장 위치
- `DART_DIR`: DART 문서 저장 위치
- `DART_API_KEY`: DART API 인증키
- `TV_KEYWORDS`: TV 관련 키워드 리스트
- `KPI_LIST`: 추출할 KPI 리스트
- `FACTOR_LIST`: 추출할 요인 리스트

## 실행 방법

### Windows (배치 파일 사용)
```cmd
setup_venv.bat              # 최초 1회 실행
run_01_consensus.bat        # Step 1
run_02_dart_metadata.bat    # Step 2
run_03_dart_documents.bat   # Step 3
```

### Python 직접 실행
```bash
python 01_crawl_consensus.py
python 02_crawl_dart_metadata.py
python 03_download_dart_documents.py
```

## 수집 데이터 요약

| 소스 | LG전자 | 삼성전자 | 합계 |
|------|--------|----------|------|
| **한경 컨센서스** | 23개 리포트<br/>26개 PDF | 45개 리포트<br/>45개 PDF | 68개 리포트<br/>71개 PDF |
| **DART** | 4개 보고서<br/>(사업 1, 반기 1, 분기 2) | 4개 보고서<br/>(사업 1, 반기 1, 분기 2) | 8개 보고서 |

**총 데이터 용량**: ~60 MB

## 다음 단계 (예정)

- [ ] Step 4: TV 관련 리포트 필터링
- [ ] Step 5: KPI-요인 관계 추출
- [ ] Step 6: Graph Database 구축
