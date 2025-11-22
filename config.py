"""
Configuration file for the project
"""

# Target companies
COMPANIES = {
    "LG전자": "006360",
    "삼성전자": "005930"
}

# TV-related keywords for filtering
TV_KEYWORDS = [
    "TV", "OLED", "디스플레이", "패널", "UHD",
    "Smart TV", "PDP", "수상기", "QLED", "Micro LED"
]

# KPI list
KPI_LIST = [
    "매출", "수익성", "ASP", "판매량", "점유율", "원가"
]

# Factor list
FACTOR_LIST = [
    "환율", "패널 가격", "프로모션", "유통사 재고",
    "마케팅비", "경쟁사 전략", "계절성"
]

# Directories
DATA_DIR = "data"
RAW_DIR = f"{DATA_DIR}/raw"
CONSENSUS_DIR = f"{RAW_DIR}/consensus"  # 한경 컨센서스 PDF 파일
DART_DIR = f"{RAW_DIR}/dart"  # DART 원문 공시 문서 (ZIP)
EXTRACTED_DIR = f"{DATA_DIR}/extracted"  # 텍스트 추출 결과
EXTRACTED_CONSENSUS_DIR = f"{EXTRACTED_DIR}/consensus"  # PDF 텍스트 추출
EXTRACTED_DART_DIR = f"{EXTRACTED_DIR}/dart"  # XML 텍스트 추출
FILTERED_DIR = f"{DATA_DIR}/filtered"
PROCESSED_DIR = f"{DATA_DIR}/processed"

# URLs
HANKYUNG_CONSENSUS_URL = "https://consensus.hankyung.com"
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"
DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"

# DART API settings
import os
DART_API_KEY = os.getenv('DART_API_KEY', 'e28a5f7e1fbead8c3403dfbf5d9d434acb32df6c')  # Use environment variable or default

# DART report types (공시상세유형)
DART_REPORT_TYPES = {
    "사업보고서": "A001",
    "반기보고서": "A002",
    "분기보고서": "A003"
}

# Crawling settings
CRAWL_DATE_RANGE_DAYS = 365  # 1 year
MAX_REPORTS_PER_COMPANY = 50  # Maximum reports to crawl per company
