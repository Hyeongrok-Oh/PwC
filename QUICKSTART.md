# 빠른 시작 가이드

## 1단계: 가상환경 설정

### Windows에서 실행:

```cmd
setup_venv.bat
```

이 스크립트는 자동으로:
- Python 가상환경 생성 (`venv` 폴더)
- pip 업그레이드
- 필요한 패키지 설치 (requirements.txt)

### 수동 설정 (또는 Linux/Mac):

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

## 2단계: 크롤러 실행

### 방법 1: Windows 배치 파일 사용 (권장)

```cmd
run_crawler.bat
```

### 방법 2: 직접 실행

```bash
# 가상환경 활성화 (이미 활성화되지 않은 경우)
venv\Scripts\activate

# 크롤러 실행
python crawler.py
```

## 3단계: 결과 확인

크롤링이 완료되면 다음 위치에서 결과를 확인할 수 있습니다:

- **메타데이터**: `data/raw/` - JSON 파일로 저장된 리포트 정보
- **PDF 파일**: `data/raw/pdfs/` - 다운로드된 PDF 리포트

## 진행상황 출력

크롤러 실행 중 터미널에 다음과 같은 정보가 표시됩니다:

```
============================================================
Hankyung Consensus Crawler
============================================================
Start time: 2025-11-21 18:40:09
Companies: LG전자, 삼성전자
Date range: Last 365 days
============================================================

============================================================
Crawling reports for LG전자
============================================================
URL: https://consensus.hankyung.com/analysis/list?...
Date range: 2024-11-21 ~ 2025-11-21
Found 23 report rows
  [1] 2025-11-10 - LG전자(066570): 이제는 AI 주식이어야 한다...
  [2] 2025-11-07 - LG전자 (066570) - 미국 내 수요 부진과 경쟁 심...

Successfully extracted 23 reports

============================================================
Downloading PDFs for LG전자
============================================================
Total reports to download: 23
============================================================

  [1/23] Downloading: LG전자_20251110_LG전자066570_이제는_AI_주식이어야_한다.pdf
           URL: https://consensus.hankyung.com/apps/...
           [OK] Downloaded: 873.2 KB
           Progress: 1 downloaded, 0 skipped, 0 failed

  [2/23] Downloading: LG전자_20251107_LG전자_066570_미국_내_수요_부진과_경쟁_심.pdf
           URL: https://consensus.hankyung.com/apps/...
           [OK] Downloaded: 570.1 KB
           Progress: 2 downloaded, 0 skipped, 0 failed

  ...

============================================================
PDF Download Summary for LG전자
============================================================
Total reports:    23
Downloaded:       23
Skipped (exists): 0
Failed:           0
============================================================
```

## 설정 변경

`config.py` 파일을 수정하여 다음을 변경할 수 있습니다:

- **대상 회사**: `COMPANIES` 딕셔너리 수정
- **수집 기간**: `CRAWL_DATE_RANGE_DAYS` 값 변경 (기본: 365일)
- **최대 리포트 수**: `MAX_REPORTS_PER_COMPANY` 값 변경 (기본: 50개)

## 문제 해결

### ChromeDriver 오류
- 첫 실행 시 ChromeDriver가 자동으로 다운로드됩니다
- 네트워크 연결을 확인하세요

### PDF 다운로드 실패
- `headless=False`로 변경하여 브라우저를 보면서 디버깅할 수 있습니다
- [crawler.py](crawler.py#L362) 362번 줄에서 수정:
  ```python
  crawler = HankyungConsensusCrawler(headless=False)
  ```

### 이미 다운로드된 파일
- 크롤러는 이미 존재하는 PDF 파일(>1KB)을 자동으로 건너뜁니다
- 재다운로드하려면 해당 PDF 파일을 삭제하세요

## 다음 단계

- **Step 2**: TV 관련 리포트 필터링 (개발 예정)
- **Step 3**: KPI-요인 관계 추출 (개발 예정)
