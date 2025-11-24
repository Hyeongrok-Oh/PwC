"""
Step 5.5: TV 관련 문단만 추출

Consensus 문서에서 TV 관련 키워드가 포함된 문단과 주변 문맥만 추출하여
별도 파일로 저장합니다. 이를 통해 LLM API 호출 시 비용을 절감할 수 있습니다.
"""

import json
import os
from datetime import datetime
from config import (
    FILTERED_DIR,
    TV_CONTENT_DIR,
    TV_CONTENT_CONSENSUS_DIR,
    EXTRACTED_CONSENSUS_DIR,
    TV_KEYWORDS
)

# 05_filter_tv_reports.py의 함수 재사용
def extract_tv_paragraphs(text, keywords, context_sentences=2):
    """
    TV 관련 키워드가 포함된 문단과 주변 문맥을 추출

    Args:
        text: 전체 텍스트
        keywords: TV 관련 키워드 리스트
        context_sentences: 키워드 전후로 포함할 문장 수

    Returns:
        dict: {
            "found_keywords": [...],
            "relevant_paragraphs": [...],
            "total_chars": int
        }
    """
    # 문단 단위로 분리 (빈 줄 기준)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    found_keywords = set()
    relevant_paragraphs = []

    for i, paragraph in enumerate(paragraphs):
        paragraph_lower = paragraph.lower()

        # 이 문단에 키워드가 있는지 확인
        keywords_in_paragraph = []
        for keyword in keywords:
            if keyword.lower() in paragraph_lower:
                keywords_in_paragraph.append(keyword)
                found_keywords.add(keyword)

        if keywords_in_paragraph:
            # 키워드가 있는 문단과 앞뒤 문단을 함께 추출
            start_idx = max(0, i - context_sentences)
            end_idx = min(len(paragraphs), i + context_sentences + 1)

            context = "\n\n".join(paragraphs[start_idx:end_idx])

            relevant_paragraphs.append({
                "paragraph_index": i,
                "keywords": keywords_in_paragraph,
                "text": context,
                "char_count": len(context)
            })

    # 중복 제거 (겹치는 문단들을 병합)
    if relevant_paragraphs:
        merged_paragraphs = [relevant_paragraphs[0]]
        for curr in relevant_paragraphs[1:]:
            prev = merged_paragraphs[-1]
            # 문단 인덱스가 가까우면 병합
            if curr["paragraph_index"] - prev["paragraph_index"] <= context_sentences * 2:
                # 키워드 합치기
                all_keywords = list(set(prev["keywords"] + curr["keywords"]))
                # 텍스트 합치기 (중복 제거)
                if prev["text"] not in curr["text"]:
                    merged_text = prev["text"] + "\n\n" + curr["text"]
                else:
                    merged_text = curr["text"]

                merged_paragraphs[-1] = {
                    "paragraph_index": prev["paragraph_index"],
                    "keywords": all_keywords,
                    "text": merged_text,
                    "char_count": len(merged_text)
                }
            else:
                merged_paragraphs.append(curr)

        relevant_paragraphs = merged_paragraphs

    total_chars = sum(p["char_count"] for p in relevant_paragraphs)

    return {
        "found_keywords": list(found_keywords),
        "relevant_paragraphs": relevant_paragraphs,
        "paragraph_count": len(relevant_paragraphs),
        "total_chars": total_chars
    }

def extract_consensus_tv_content():
    """Consensus 문서에서 TV 관련 문단만 추출"""

    print("=" * 80)
    print("Step 5.5: Consensus TV 관련 문단 추출")
    print("=" * 80)
    print(f"\nTV 키워드: {', '.join(TV_KEYWORDS)}")
    print(f"주변 문맥: 키워드 포함 문단만 (주변 문맥 0개)\n")

    # filtered_index.json 로드
    filtered_index_path = f"{FILTERED_DIR}/filtered_index.json"
    if not os.path.exists(filtered_index_path):
        print(f"[ERROR] {filtered_index_path} 파일을 찾을 수 없습니다.")
        print("먼저 05_filter_tv_reports.py를 실행해주세요.")
        return

    with open(filtered_index_path, 'r', encoding='utf-8') as f:
        filtered_data = json.load(f)

    consensus_reports = filtered_data["filtered_reports"]["consensus"]

    # 출력 디렉토리 생성
    os.makedirs(TV_CONTENT_CONSENSUS_DIR, exist_ok=True)

    # 통계
    stats = {
        "total_documents": 0,
        "total_original_chars": 0,
        "total_tv_chars": 0,
        "avg_reduction_rate": 0,
        "by_company": {}
    }

    documents_info = []

    print(f"처리할 Consensus 문서: {len(consensus_reports)}개\n")

    # 각 문서 처리
    for idx, report in enumerate(consensus_reports, 1):
        filename = report["filename"]
        company = report["company"]
        date = report["date"]
        original_file_path = report["file_path"]

        print(f"[{idx}/{len(consensus_reports)}] {filename}")

        # 회사별 통계 초기화
        if company not in stats["by_company"]:
            stats["by_company"][company] = {
                "count": 0,
                "original_chars": 0,
                "tv_chars": 0
            }

        # 원본 텍스트 로드
        try:
            with open(original_file_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)

            original_text = original_data.get("text", "")
            original_char_count = len(original_text)

            # TV 관련 문단 추출 (주변 문맥 0개)
            tv_result = extract_tv_paragraphs(original_text, TV_KEYWORDS, context_sentences=0)

            tv_char_count = tv_result["total_chars"]
            reduction_rate = ((original_char_count - tv_char_count) / original_char_count * 100) if original_char_count > 0 else 0

            # 결과 저장
            output_filename = filename.replace(".pdf", "_tv_content.json")
            output_path = f"{TV_CONTENT_CONSENSUS_DIR}/{output_filename}"

            output_data = {
                "source": "consensus",
                "filename": filename,
                "company": company,
                "date": date,
                "original_char_count": original_char_count,
                "tv_content": {
                    "found_keywords": tv_result["found_keywords"],
                    "paragraphs": tv_result["relevant_paragraphs"],
                    "total_char_count": tv_char_count,
                    "paragraph_count": tv_result["paragraph_count"],
                    "reduction_rate": round(reduction_rate, 1)
                },
                "extracted_at": datetime.now().isoformat()
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            # 통계 업데이트
            stats["total_documents"] += 1
            stats["total_original_chars"] += original_char_count
            stats["total_tv_chars"] += tv_char_count
            stats["by_company"][company]["count"] += 1
            stats["by_company"][company]["original_chars"] += original_char_count
            stats["by_company"][company]["tv_chars"] += tv_char_count

            # 문서 정보 저장
            documents_info.append({
                "filename": filename,
                "company": company,
                "date": date,
                "original_chars": original_char_count,
                "tv_chars": tv_char_count,
                "reduction_rate": round(reduction_rate, 1),
                "keywords": tv_result["found_keywords"],
                "paragraph_count": tv_result["paragraph_count"],
                "output_file": output_filename
            })

            print(f"  원본: {original_char_count:,}자 → TV 문단: {tv_char_count:,}자 ({reduction_rate:.1f}% 감소)")
            print(f"  키워드: {', '.join(tv_result['found_keywords'])}")
            print(f"  문단: {tv_result['paragraph_count']}개\n")

        except Exception as e:
            print(f"  [ERROR] 처리 실패: {str(e)}\n")
            continue

    # 평균 감소율 계산
    if stats["total_original_chars"] > 0:
        overall_reduction = (stats["total_original_chars"] - stats["total_tv_chars"]) / stats["total_original_chars"] * 100
        stats["avg_reduction_rate"] = round(overall_reduction, 1)

    # 통합 인덱스 생성
    tv_content_index = {
        "metadata": {
            "description": "TV 관련 문단만 추출한 Consensus 리포트",
            "tv_keywords": TV_KEYWORDS,
            "context_sentences": 0,
            "extraction_date": datetime.now().isoformat()
        },
        "statistics": {
            "total_documents": stats["total_documents"],
            "total_original_chars": stats["total_original_chars"],
            "total_tv_chars": stats["total_tv_chars"],
            "chars_reduced": stats["total_original_chars"] - stats["total_tv_chars"],
            "avg_reduction_rate": stats["avg_reduction_rate"],
            "by_company": stats["by_company"]
        },
        "documents": documents_info
    }

    # 인덱스 저장
    index_path = f"{TV_CONTENT_DIR}/tv_content_index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(tv_content_index, f, ensure_ascii=False, indent=2)

    # 최종 통계 출력
    print("=" * 80)
    print("추출 완료!")
    print("=" * 80)
    print(f"\n[전체 통계]")
    print(f"  처리된 문서: {stats['total_documents']}개")
    print(f"  원본 총 글자 수: {stats['total_original_chars']:,}자")
    print(f"  TV 문단 총 글자 수: {stats['total_tv_chars']:,}자")
    print(f"  감소된 글자 수: {stats['total_original_chars'] - stats['total_tv_chars']:,}자")
    print(f"  평균 감소율: {stats['avg_reduction_rate']}%")

    print(f"\n[회사별 통계]")
    for company, company_stats in stats["by_company"].items():
        company_reduction = ((company_stats["original_chars"] - company_stats["tv_chars"]) /
                           company_stats["original_chars"] * 100) if company_stats["original_chars"] > 0 else 0
        print(f"  {company}:")
        print(f"    문서 수: {company_stats['count']}개")
        print(f"    원본: {company_stats['original_chars']:,}자")
        print(f"    TV 문단: {company_stats['tv_chars']:,}자")
        print(f"    감소율: {company_reduction:.1f}%")

    print(f"\n[저장 위치]")
    print(f"  문서: {TV_CONTENT_CONSENSUS_DIR}/")
    print(f"  인덱스: {index_path}")

    # 비용 절감 예측
    print(f"\n[예상 비용 절감]")
    tokens_saved = (stats['total_original_chars'] - stats['total_tv_chars']) * 1.5 / 1000
    print(f"  절감 토큰 (한글 1.5배 환산): {tokens_saved:,.0f}K tokens")
    print(f"  GPT-4 기준: ${tokens_saved * 0.03:,.2f} 절감")
    print(f"  Claude 3.5 Sonnet 기준: ${tokens_saved * 0.003:,.2f} 절감")
    print(f"  Gemini Pro 1.5 기준: ${tokens_saved * 0.00125:,.2f} 절감")

if __name__ == "__main__":
    extract_consensus_tv_content()
