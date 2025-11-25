"""
Step 6: KPI-Factor 추출

TV 관련 문단에서 Gemini API를 사용하여 KPI-Factor 관계를 추출합니다.
"""

import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from config import (
    TV_CONTENT_DIR,
    TV_CONTENT_CONSENSUS_DIR,
    PROCESSED_DIR,
    GEMINI_API_KEY,
    KPI_LIST,
    FACTOR_LIST
)

# .env 파일 로드
load_dotenv()

# Gemini API 설정
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

genai.configure(api_key=GEMINI_API_KEY)

# Gemini Flash 2.5 모델 사용
MODEL_NAME = "gemini-2.0-flash-exp"

# 프롬프트 템플릿
EXTRACTION_PROMPT = """당신은 TV 산업 애널리스트 리포트를 분석하는 전문가입니다.

다음 텍스트에서 TV 사업과 관련된 **KPI(핵심성과지표)**와 **Factor(영향요인)** 간의 관계를 추출해주세요.

# KPI 목록
{kpi_list}

# Factor 목록
{factor_list}

# 분석할 텍스트
회사: {company}
날짜: {date}
내용:
{text}

# 출력 형식 (JSON)
다음 JSON 형식으로 출력해주세요. 문서에서 명확하게 언급된 관계만 추출하세요.

{{
  "kpi_factor_relations": [
    {{
      "kpi": "매출",
      "factor": "환율",
      "relation": "positive/negative/neutral",
      "evidence": "텍스트에서 발췌한 근거 문장",
      "confidence": "high/medium/low"
    }}
  ],
  "key_insights": [
    "문서의 주요 인사이트 1",
    "문서의 주요 인사이트 2"
  ]
}}

**중요:**
1. 텍스트에서 명확하게 언급된 관계만 추출하세요.
2. relation은 "positive" (긍정적 영향), "negative" (부정적 영향), "neutral" (중립적 언급) 중 하나로 표시하세요.
3. evidence는 원문에서 해당 관계를 뒷받침하는 문장을 그대로 발췌하세요.
4. confidence는 해당 관계의 신뢰도를 "high", "medium", "low"로 표시하세요.
5. 추측이나 일반적인 상식이 아닌, 문서에 명시된 내용만 추출하세요.
6. JSON 형식만 출력하고, 다른 설명은 추가하지 마세요.
"""

def extract_kpi_factors_from_text(text, company, date, model, max_retries=3):
    """텍스트에서 KPI-Factor 관계 추출 (retry 로직 포함)"""

    prompt = EXTRACTION_PROMPT.format(
        kpi_list=", ".join(KPI_LIST),
        factor_list=", ".join(FACTOR_LIST),
        company=company,
        date=date,
        text=text
    )

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)

            # JSON 파싱
            response_text = response.text.strip()

            # Markdown code block 제거 (```json ... ```)
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()

            result = json.loads(response_text)

            return result, response.usage_metadata

        except json.JSONDecodeError as e:
            print(f"  [WARNING] JSON 파싱 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                print(f"  응답 텍스트: {response.text[:200]}...")
                return None, None

        except Exception as e:
            error_msg = str(e)

            # Rate limit 에러 체크 (429)
            if "429" in error_msg or "quota" in error_msg.lower():
                # retry_delay 추출 시도
                import re
                delay_match = re.search(r'retry_delay.*?seconds: (\d+)', error_msg)

                if delay_match:
                    delay_seconds = int(delay_match.group(1)) + 5  # 여유 5초 추가
                else:
                    delay_seconds = 60  # 기본 60초

                if attempt < max_retries - 1:
                    print(f"  [RATE_LIMIT] API 제한 도달. {delay_seconds}초 대기 후 재시도 ({attempt + 1}/{max_retries})...")
                    time.sleep(delay_seconds)
                    continue
                else:
                    print(f"  [ERROR] 최대 재시도 횟수 초과")
                    return None, None
            else:
                print(f"  [ERROR] API 호출 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    return None, None

    return None, None

def extract_kpi_factors():
    """TV 문단에서 KPI-Factor 관계 추출"""

    print("=" * 80)
    print("Step 6: KPI-Factor 추출 (Rate Limit 자동 대응)")
    print("=" * 80)
    print(f"\n모델: {MODEL_NAME}")
    print(f"KPI 목록: {', '.join(KPI_LIST)}")
    print(f"Factor 목록: {', '.join(FACTOR_LIST)}")
    print(f"최대 재시도: 3회")
    print(f"Rate Limit 시 자동 대기 후 재시도\n")

    # TV content index 로드
    tv_content_index_path = f"{TV_CONTENT_DIR}/tv_content_index.json"
    if not os.path.exists(tv_content_index_path):
        print(f"[ERROR] {tv_content_index_path} 파일을 찾을 수 없습니다.")
        print("먼저 06_extract_tv_content.py를 실행해주세요.")
        return

    with open(tv_content_index_path, 'r', encoding='utf-8') as f:
        tv_content_index = json.load(f)

    documents = tv_content_index["documents"]

    # Gemini 모델 초기화
    model = genai.GenerativeModel(MODEL_NAME)

    # 출력 디렉토리 생성
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    kpi_factors_dir = f"{PROCESSED_DIR}/kpi_factors"
    os.makedirs(kpi_factors_dir, exist_ok=True)

    # 통계
    stats = {
        "total_documents": 0,
        "successful_extractions": 0,
        "failed_extractions": 0,
        "total_relations": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "by_company": {}
    }

    results = []

    print(f"처리할 문서: {len(documents)}개\n")

    # 각 문서 처리
    for idx, doc in enumerate(documents, 1):
        filename = doc["filename"]
        company = doc["company"]
        date = doc["date"]
        tv_char_count = doc["tv_chars"]

        print(f"[{idx}/{len(documents)}] {filename}")

        # 회사별 통계 초기화
        if company not in stats["by_company"]:
            stats["by_company"][company] = {
                "count": 0,
                "successful": 0,
                "relations": 0
            }

        stats["total_documents"] += 1
        stats["by_company"][company]["count"] += 1

        # TV content 파일 로드
        tv_content_path = f"{TV_CONTENT_CONSENSUS_DIR}/{doc['output_file']}"

        try:
            with open(tv_content_path, 'r', encoding='utf-8') as f:
                tv_content = json.load(f)

            # TV 문단들을 하나의 텍스트로 합치기
            paragraphs = tv_content["tv_content"]["paragraphs"]
            combined_text = "\n\n".join([p["text"] for p in paragraphs])

            # Gemini API 호출
            extraction_result, usage = extract_kpi_factors_from_text(
                combined_text, company, date, model
            )

            if extraction_result:
                stats["successful_extractions"] += 1
                stats["by_company"][company]["successful"] += 1

                relations_count = len(extraction_result.get("kpi_factor_relations", []))
                stats["total_relations"] += relations_count
                stats["by_company"][company]["relations"] += relations_count

                # Usage 통계
                if usage:
                    stats["total_input_tokens"] += usage.prompt_token_count
                    stats["total_output_tokens"] += usage.candidates_token_count

                # 결과 저장
                output_filename = filename.replace(".pdf", "_kpi_factors.json")
                output_path = f"{kpi_factors_dir}/{output_filename}"

                output_data = {
                    "source": "consensus",
                    "filename": filename,
                    "company": company,
                    "date": date,
                    "tv_char_count": tv_char_count,
                    "extraction": extraction_result,
                    "metadata": {
                        "model": MODEL_NAME,
                        "extracted_at": datetime.now().isoformat(),
                        "input_tokens": usage.prompt_token_count if usage else None,
                        "output_tokens": usage.candidates_token_count if usage else None
                    }
                }

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

                # 결과 리스트에 추가
                results.append({
                    "filename": filename,
                    "company": company,
                    "date": date,
                    "relations_count": relations_count,
                    "output_file": output_filename
                })

                print(f"  [OK] 추출 성공: {relations_count}개 관계")
                if usage:
                    print(f"  토큰: {usage.prompt_token_count} in / {usage.candidates_token_count} out")

            else:
                stats["failed_extractions"] += 1
                print(f"  [FAIL] 추출 실패")

        except Exception as e:
            stats["failed_extractions"] += 1
            print(f"  [ERROR] 처리 실패: {str(e)}")

        print()

    # 통합 인덱스 생성
    kpi_factors_index = {
        "metadata": {
            "description": "TV 관련 문단에서 추출한 KPI-Factor 관계",
            "model": MODEL_NAME,
            "kpi_list": KPI_LIST,
            "factor_list": FACTOR_LIST,
            "extraction_date": datetime.now().isoformat()
        },
        "statistics": stats,
        "results": results
    }

    # 인덱스 저장
    index_path = f"{PROCESSED_DIR}/kpi_factors_index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(kpi_factors_index, f, ensure_ascii=False, indent=2)

    # 최종 통계 출력
    print("=" * 80)
    print("추출 완료!")
    print("=" * 80)
    print(f"\n[전체 통계]")
    print(f"  처리된 문서: {stats['total_documents']}개")
    print(f"  성공: {stats['successful_extractions']}개")
    print(f"  실패: {stats['failed_extractions']}개")
    print(f"  추출된 관계: {stats['total_relations']}개")

    print(f"\n[토큰 사용량]")
    print(f"  입력 토큰: {stats['total_input_tokens']:,}")
    print(f"  출력 토큰: {stats['total_output_tokens']:,}")
    print(f"  총 토큰: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")

    print(f"\n[회사별 통계]")
    for company, company_stats in stats["by_company"].items():
        print(f"  {company}:")
        print(f"    문서: {company_stats['count']}개 (성공: {company_stats['successful']}개)")
        print(f"    관계: {company_stats['relations']}개")

    print(f"\n[저장 위치]")
    print(f"  문서: {kpi_factors_dir}/")
    print(f"  인덱스: {index_path}")

    # 비용 계산 (Gemini Flash 2.5 pricing)
    # Input: $0.075 per 1M tokens (128K context)
    # Output: $0.30 per 1M tokens
    input_cost = stats['total_input_tokens'] / 1_000_000 * 0.075
    output_cost = stats['total_output_tokens'] / 1_000_000 * 0.30
    total_cost = input_cost + output_cost

    print(f"\n[예상 비용 (Gemini Flash 2.5)]")
    print(f"  입력: ${input_cost:.4f}")
    print(f"  출력: ${output_cost:.4f}")
    print(f"  총계: ${total_cost:.4f}")

if __name__ == "__main__":
    extract_kpi_factors()
