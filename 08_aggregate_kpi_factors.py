"""
Step 7: KPI-Factor 집계

개별 문서에서 추출된 모든 KPI-Factor를 통합 인덱스에 집계합니다.
"""

import json
import os
from collections import defaultdict
from config import PROCESSED_DIR

def aggregate_kpi_factors():
    """개별 KPI-Factor 파일에서 모든 관계를 집계"""

    print("=" * 80)
    print("Step 7: KPI-Factor 집계")
    print("=" * 80)
    print()

    # 기존 인덱스 로드
    index_path = f"{PROCESSED_DIR}/kpi_factors_index.json"
    if not os.path.exists(index_path):
        print(f"[ERROR] {index_path} 파일을 찾을 수 없습니다.")
        print("먼저 07_extract_kpi_factors.py를 실행해주세요.")
        return

    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    kpi_factors_dir = f"{PROCESSED_DIR}/kpi_factors"

    # 모든 관계 수집
    all_relations = []
    unique_kpis = set()
    unique_factors = set()

    # KPI-Factor 조합별 통계
    kpi_factor_stats = defaultdict(lambda: {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "total": 0,
        "examples": []
    })

    # 회사별 통계
    company_stats = defaultdict(lambda: {
        "kpis": set(),
        "factors": set(),
        "relations": []
    })

    print(f"처리할 문서: {len(index_data['results'])}개\n")

    # 각 결과 파일 처리
    for idx, result in enumerate(index_data['results'], 1):
        output_file = result['output_file']
        filepath = f"{kpi_factors_dir}/{output_file}"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)

            company = doc_data['company']
            date = doc_data['date']
            filename = doc_data['filename']

            # KPI-Factor 관계 추출
            relations = doc_data['extraction'].get('kpi_factor_relations', [])

            if relations:
                print(f"[{idx}/{len(index_data['results'])}] {filename}: {len(relations)}개 관계")

            for rel in relations:
                kpi = rel['kpi']
                factor = rel['factor']
                relation = rel['relation']
                evidence = rel.get('evidence', '')
                confidence = rel.get('confidence', 'unknown')

                # 유니크 KPI/Factor 추가
                unique_kpis.add(kpi)
                unique_factors.add(factor)

                # 전체 관계 리스트에 추가
                relation_record = {
                    "company": company,
                    "date": date,
                    "filename": filename,
                    "kpi": kpi,
                    "factor": factor,
                    "relation": relation,
                    "evidence": evidence,
                    "confidence": confidence
                }
                all_relations.append(relation_record)

                # KPI-Factor 조합별 통계
                key = f"{kpi}|{factor}"
                kpi_factor_stats[key]["total"] += 1
                kpi_factor_stats[key][relation] += 1

                # 예시는 최대 3개까지만 저장 (high confidence 우선)
                if len(kpi_factor_stats[key]["examples"]) < 3:
                    kpi_factor_stats[key]["examples"].append({
                        "company": company,
                        "date": date,
                        "relation": relation,
                        "evidence": evidence[:100] + "..." if len(evidence) > 100 else evidence,
                        "confidence": confidence
                    })

                # 회사별 통계
                company_stats[company]["kpis"].add(kpi)
                company_stats[company]["factors"].add(factor)
                company_stats[company]["relations"].append(relation_record)

        except Exception as e:
            print(f"[ERROR] {output_file} 처리 실패: {str(e)}")

    print()
    print("=" * 80)

    # KPI-Factor 조합별 통계를 리스트로 변환 (정렬용)
    kpi_factor_summary = []
    for key, stats in kpi_factor_stats.items():
        kpi, factor = key.split("|")
        kpi_factor_summary.append({
            "kpi": kpi,
            "factor": factor,
            "total_mentions": stats["total"],
            "positive": stats["positive"],
            "negative": stats["negative"],
            "neutral": stats["neutral"],
            "examples": stats["examples"]
        })

    # 빈도순으로 정렬
    kpi_factor_summary.sort(key=lambda x: x["total_mentions"], reverse=True)

    # 회사별 통계를 JSON 직렬화 가능하게 변환
    company_summary = {}
    for company, stats in company_stats.items():
        company_summary[company] = {
            "unique_kpis": sorted(list(stats["kpis"])),
            "unique_factors": sorted(list(stats["factors"])),
            "kpi_count": len(stats["kpis"]),
            "factor_count": len(stats["factors"]),
            "relation_count": len(stats["relations"])
        }

    # 집계 결과 생성
    aggregated_data = {
        "metadata": {
            "description": "개별 문서에서 추출된 모든 KPI-Factor 관계의 집계",
            "aggregation_date": index_data['metadata']['extraction_date'],
            "source_index": "kpi_factors_index.json"
        },
        "summary": {
            "total_relations": len(all_relations),
            "unique_kpis": sorted(list(unique_kpis)),
            "unique_factors": sorted(list(unique_factors)),
            "unique_kpi_count": len(unique_kpis),
            "unique_factor_count": len(unique_factors),
            "total_documents": len(index_data['results'])
        },
        "by_company": company_summary,
        "kpi_factor_combinations": kpi_factor_summary,
        "all_relations": all_relations
    }

    # 집계 결과 저장
    output_path = f"{PROCESSED_DIR}/kpi_factors_aggregated.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(aggregated_data, f, ensure_ascii=False, indent=2)

    # 통계 출력
    print("집계 완료!")
    print("=" * 80)
    print(f"\n[전체 통계]")
    print(f"  총 관계: {len(all_relations)}개")
    print(f"  유니크 KPI: {len(unique_kpis)}개")
    print(f"  유니크 Factor: {len(unique_factors)}개")
    print(f"  KPI-Factor 조합: {len(kpi_factor_summary)}개")

    print(f"\n[추출된 KPI 목록]")
    for kpi in sorted(list(unique_kpis)):
        kpi_count = sum(1 for r in all_relations if r['kpi'] == kpi)
        print(f"  - {kpi}: {kpi_count}회 언급")

    print(f"\n[추출된 Factor 목록]")
    for factor in sorted(list(unique_factors)):
        factor_count = sum(1 for r in all_relations if r['factor'] == factor)
        print(f"  - {factor}: {factor_count}회 언급")

    print(f"\n[회사별 통계]")
    for company, stats in company_summary.items():
        print(f"  {company}:")
        print(f"    유니크 KPI: {stats['kpi_count']}개")
        print(f"    유니크 Factor: {stats['factor_count']}개")
        print(f"    총 관계: {stats['relation_count']}개")

    print(f"\n[가장 많이 언급된 KPI-Factor 조합 TOP 10]")
    for i, combo in enumerate(kpi_factor_summary[:10], 1):
        print(f"  {i}. {combo['kpi']} - {combo['factor']}: {combo['total_mentions']}회")
        print(f"     (긍정: {combo['positive']}, 부정: {combo['negative']}, 중립: {combo['neutral']})")

    print(f"\n[저장 위치]")
    print(f"  {output_path}")

    return aggregated_data

if __name__ == "__main__":
    aggregate_kpi_factors()
