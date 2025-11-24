"""
Step 5: TV 관련 리포트 필터링

추출된 텍스트에서 TV 관련 키워드를 포함하는 리포트만 필터링합니다.
"""

import json
import os
from pathlib import Path
from config import (
    EXTRACTED_DIR,
    EXTRACTED_CONSENSUS_DIR,
    EXTRACTED_DART_DIR,
    FILTERED_DIR,
    TV_KEYWORDS
)

def load_extracted_data(index_path):
    """추출된 데이터 인덱스 로드"""
    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_tv_keywords(text, keywords):
    """텍스트에 TV 관련 키워드가 포함되어 있는지 확인"""
    text_lower = text.lower()
    found_keywords = []

    for keyword in keywords:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)

    return found_keywords

def filter_tv_reports():
    """TV 관련 리포트 필터링"""

    # 인덱스 파일 로드
    index_path = f"{EXTRACTED_DIR}/index.json"
    if not os.path.exists(index_path):
        print(f"[ERROR] 인덱스 파일을 찾을 수 없습니다: {index_path}")
        return

    print("=" * 80)
    print("Step 5: TV 관련 리포트 필터링")
    print("=" * 80)
    print(f"\nTV 키워드 목록: {', '.join(TV_KEYWORDS)}")
    print(f"총 {len(TV_KEYWORDS)}개 키워드\n")

    index_data = load_extracted_data(index_path)

    # 필터링 결과 저장
    filtered_reports = {
        "consensus": [],
        "dart": []
    }

    stats = {
        "total": 0,
        "filtered": 0,
        "by_source": {"consensus": 0, "dart": 0},
        "by_company": {}
    }

    # Consensus 문서 처리
    for doc in index_data.get("consensus", []):
        stats["total"] += 1
        source = "consensus"
        company = doc["company"]

        # 회사별 통계 초기화
        if company not in stats["by_company"]:
            stats["by_company"][company] = {"total": 0, "filtered": 0}
        stats["by_company"][company]["total"] += 1

        # 추출된 텍스트 파일 로드
        extracted_file = doc.get("extracted_file", "")
        file_path = f"{EXTRACTED_CONSENSUS_DIR}/{extracted_file}"

        if not os.path.exists(file_path):
            print(f"[SKIP] 파일을 찾을 수 없음: {file_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)

        # TV 키워드 검색
        text = extracted_data.get("text", "")
        found_keywords = check_tv_keywords(text, TV_KEYWORDS)

        if found_keywords:
            stats["filtered"] += 1
            stats["by_source"][source] += 1
            stats["by_company"][company]["filtered"] += 1

            # 필터링된 리포트 정보 저장
            filtered_info = {
                "filename": doc["filename"],
                "company": company,
                "date": doc.get("date", ""),
                "file_path": file_path,
                "char_count": extracted_data.get("char_count", 0),
                "found_keywords": found_keywords,
                "keyword_count": len(found_keywords)
            }

            filtered_reports[source].append(filtered_info)

            print(f"[+] [{source.upper()}] {doc['filename']}")
            print(f"    키워드: {', '.join(found_keywords)}")

    # DART 문서 처리
    for doc in index_data.get("dart", []):
        stats["total"] += 1
        source = "dart"

        # zip_file 이름에서 회사명 추출
        zip_file = doc.get("zip_file", "")
        if "LG전자" in zip_file:
            company = "LG전자"
        elif "삼성전자" in zip_file:
            company = "삼성전자"
        else:
            company = "Unknown"

        # 회사별 통계 초기화
        if company not in stats["by_company"]:
            stats["by_company"][company] = {"total": 0, "filtered": 0}
        stats["by_company"][company]["total"] += 1

        # 추출된 텍스트 파일 로드
        extracted_file = doc.get("extracted_file", "")
        file_path = f"{EXTRACTED_DART_DIR}/{extracted_file}"

        if not os.path.exists(file_path):
            print(f"[SKIP] 파일을 찾을 수 없음: {file_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)

        # TV 키워드 검색
        text = extracted_data.get("text", "")
        found_keywords = check_tv_keywords(text, TV_KEYWORDS)

        if found_keywords:
            stats["filtered"] += 1
            stats["by_source"][source] += 1
            stats["by_company"][company]["filtered"] += 1

            # 필터링된 리포트 정보 저장
            filtered_info = {
                "filename": zip_file,
                "company": company,
                "rcept_no": doc.get("rcept_no", ""),
                "file_path": file_path,
                "char_count": extracted_data.get("total_chars", 0),
                "found_keywords": found_keywords,
                "keyword_count": len(found_keywords)
            }

            filtered_reports[source].append(filtered_info)

            print(f"[+] [{source.upper()}] {zip_file}")
            print(f"    키워드: {', '.join(found_keywords)}")

    # 결과 통계 출력
    print("\n" + "=" * 80)
    print("필터링 결과")
    print("=" * 80)
    print(f"\n[전체 통계]")
    print(f"  - 전체 문서: {stats['total']}개")
    print(f"  - TV 관련 문서: {stats['filtered']}개 ({stats['filtered']/stats['total']*100:.1f}%)")

    print(f"\n[소스별 통계]")
    consensus_total = len(index_data.get("consensus", []))
    dart_total = len(index_data.get("dart", []))
    print(f"  - Consensus: {stats['by_source']['consensus']}/{consensus_total}개")
    print(f"  - DART: {stats['by_source']['dart']}/{dart_total}개")

    print(f"\n[회사별 통계]")
    for company, company_stats in stats["by_company"].items():
        print(f"  - {company}: {company_stats['filtered']}/{company_stats['total']}개 "
              f"({company_stats['filtered']/company_stats['total']*100:.1f}%)")

    # 필터링된 데이터 저장
    os.makedirs(FILTERED_DIR, exist_ok=True)

    from datetime import datetime

    filtered_index = {
        "metadata": {
            "description": "TV 관련 키워드로 필터링된 리포트",
            "tv_keywords": TV_KEYWORDS,
            "filter_date": datetime.now().isoformat()
        },
        "statistics": stats,
        "filtered_reports": filtered_reports
    }

    output_path = f"{FILTERED_DIR}/filtered_index.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_index, f, ensure_ascii=False, indent=2)

    print(f"\n[저장 완료] {output_path}")

    # 데이터 충분성 판단
    print("\n" + "=" * 80)
    print("데이터 충분성 평가")
    print("=" * 80)

    min_threshold = 10  # 최소 필요 문서 수
    recommended_threshold = 20  # 권장 문서 수

    if stats['filtered'] < min_threshold:
        print(f"[!] 필터링된 문서가 {stats['filtered']}개로 부족합니다. (최소 {min_threshold}개 권장)")
        print("    크롤링 기간을 늘려서 더 많은 데이터를 수집하는 것을 권장합니다.")
        return False
    elif stats['filtered'] < recommended_threshold:
        print(f"[!] 필터링된 문서가 {stats['filtered']}개입니다. (권장: {recommended_threshold}개 이상)")
        print("    분석은 가능하지만, 더 많은 데이터가 있으면 더 좋은 결과를 얻을 수 있습니다.")
        return True
    else:
        print(f"[OK] 필터링된 문서가 {stats['filtered']}개로 충분합니다!")
        return True

if __name__ == "__main__":
    is_sufficient = filter_tv_reports()

    if not is_sufficient:
        print("\n다음 단계: 01_crawl_consensus.py에서 크롤링 기간을 늘려주세요.")
    else:
        print("\n[OK] Step 6 (KPI-Factor 추출)로 진행할 수 있습니다.")
