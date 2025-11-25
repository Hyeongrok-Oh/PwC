"""
Step 8: Graph 생성 및 시각화

KPI-Factor 관계 데이터를 Graph 형태로 시각화하고 Graph RAG를 위한 데이터를 준비합니다.
"""

import json
import os
import networkx as nx
import plotly.graph_objects as go
from collections import defaultdict
import community as community_louvain
from config import PROCESSED_DIR

def create_graph_from_data(aggregated_data):
    """집계된 데이터에서 NetworkX 그래프 생성"""

    G = nx.DiGraph()  # 방향성 그래프 (KPI <- Factor 영향)

    # 노드 타입별 카운터
    node_stats = defaultdict(int)
    edge_stats = defaultdict(int)

    # 회사 노드 추가
    for company in aggregated_data['by_company'].keys():
        G.add_node(company, node_type='company', label=company)
        node_stats['company'] += 1

    # KPI 노드 추가
    for kpi in aggregated_data['summary']['unique_kpis']:
        G.add_node(f"KPI_{kpi}", node_type='kpi', label=kpi, name=kpi)
        node_stats['kpi'] += 1

    # Factor 노드 추가
    for factor in aggregated_data['summary']['unique_factors']:
        G.add_node(f"Factor_{factor}", node_type='factor', label=factor, name=factor)
        node_stats['factor'] += 1

    # 관계(엣지) 추가
    for relation in aggregated_data['all_relations']:
        company = relation['company']
        kpi = relation['kpi']
        factor = relation['factor']
        relation_type = relation['relation']
        evidence = relation['evidence']
        confidence = relation['confidence']
        date = relation['date']
        filename = relation['filename']

        kpi_node = f"KPI_{kpi}"
        factor_node = f"Factor_{factor}"

        # Company -> KPI 엣지
        if not G.has_edge(company, kpi_node):
            G.add_edge(company, kpi_node, edge_type='has_kpi', weight=1)
            edge_stats['company_kpi'] += 1

        # Company -> Factor 엣지
        if not G.has_edge(company, factor_node):
            G.add_edge(company, factor_node, edge_type='has_factor', weight=1)
            edge_stats['company_factor'] += 1

        # Factor -> KPI 영향 관계 (핵심 엣지)
        edge_key = (factor_node, kpi_node, relation_type)

        if G.has_edge(factor_node, kpi_node):
            # 기존 엣지에 정보 추가
            edge_data = G[factor_node][kpi_node]
            edge_data['weight'] += 1
            edge_data['evidences'].append({
                'company': company,
                'date': date,
                'filename': filename,
                'evidence': evidence,
                'confidence': confidence
            })
        else:
            # 새 엣지 생성
            G.add_edge(
                factor_node,
                kpi_node,
                edge_type='influences',
                relation=relation_type,
                weight=1,
                evidences=[{
                    'company': company,
                    'date': date,
                    'filename': filename,
                    'evidence': evidence,
                    'confidence': confidence
                }]
            )
            edge_stats[f'influence_{relation_type}'] += 1

    return G, node_stats, edge_stats


def create_interactive_visualization(G, output_path):
    """Plotly를 사용한 인터랙티브 시각화 생성"""

    # Spring layout으로 노드 위치 계산
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # 엣지 데이터 준비
    edge_traces = []

    # 엣지 타입별로 분리
    for edge in G.edges(data=True):
        source, target, data = edge
        edge_type = data.get('edge_type', 'unknown')

        x0, y0 = pos[source]
        x1, y1 = pos[target]

        # 색상 설정
        if edge_type == 'influences':
            relation = data.get('relation', 'neutral')
            if relation == 'positive':
                color = 'green'
                width = 2
            elif relation == 'negative':
                color = 'red'
                width = 2
            else:
                color = 'gray'
                width = 1
        else:
            color = 'lightgray'
            width = 0.5

        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=width, color=color),
            hoverinfo='none',
            showlegend=False,
            opacity=0.5
        )
        edge_traces.append(edge_trace)

    # 노드 데이터 준비 (타입별로 분리)
    node_traces = {}

    for node in G.nodes(data=True):
        node_id, data = node
        node_type = data.get('node_type', 'unknown')

        if node_type not in node_traces:
            node_traces[node_type] = {
                'x': [],
                'y': [],
                'text': [],
                'size': [],
                'customdata': []
            }

        x, y = pos[node_id]
        label = data.get('label', node_id)

        # 노드 크기 (연결 개수에 비례)
        degree = G.degree(node_id)
        size = 10 + degree * 2

        # Hover 텍스트
        hover_text = f"{label}<br>타입: {node_type}<br>연결: {degree}개"

        node_traces[node_type]['x'].append(x)
        node_traces[node_type]['y'].append(y)
        node_traces[node_type]['text'].append(hover_text)
        node_traces[node_type]['size'].append(size)
        node_traces[node_type]['customdata'].append(node_id)

    # 노드 타입별 색상
    node_colors = {
        'company': '#1f77b4',  # 파란색
        'kpi': '#ff7f0e',      # 주황색
        'factor': '#2ca02c'    # 녹색
    }

    # Plotly Figure 생성
    fig = go.Figure()

    # 엣지 추가
    for trace in edge_traces:
        fig.add_trace(trace)

    # 노드 추가 (타입별)
    for node_type, trace_data in node_traces.items():
        fig.add_trace(go.Scatter(
            x=trace_data['x'],
            y=trace_data['y'],
            mode='markers+text',
            name=node_type.upper(),
            text=[data.get('label', data.get('name', '')) for node, data in G.nodes(data=True) if data.get('node_type') == node_type],
            textposition="top center",
            hovertext=trace_data['text'],
            hoverinfo='text',
            marker=dict(
                size=trace_data['size'],
                color=node_colors.get(node_type, 'gray'),
                line=dict(width=2, color='white')
            ),
            customdata=trace_data['customdata']
        ))

    # 레이아웃 설정
    fig.update_layout(
        title={
            'text': 'KPI-Factor 관계 그래프<br><sub>LG전자 & 삼성전자 TV 사업 분석</sub>',
            'x': 0.5,
            'xanchor': 'center'
        },
        showlegend=True,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=80),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        width=1400,
        height=900,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    # HTML 파일로 저장
    fig.write_html(output_path)
    print(f"  시각화 저장: {output_path}")

    return fig


def export_for_graph_rag(G, output_path):
    """Graph RAG를 위한 GraphML 형식으로 저장"""

    # GraphML은 리스트 타입을 지원하지 않으므로 JSON 문자열로 변환
    G_export = G.copy()
    for u, v, data in G_export.edges(data=True):
        if 'evidences' in data:
            # evidences 리스트를 JSON 문자열로 변환
            data['evidences'] = json.dumps(data['evidences'], ensure_ascii=False)

    # GraphML로 저장 (LangChain, LlamaIndex와 호환)
    nx.write_graphml(G_export, output_path)
    print(f"  GraphML 저장: {output_path}")


def analyze_graph(G):
    """그래프 통계 분석"""

    print("\n[그래프 통계]")
    print(f"  노드 수: {G.number_of_nodes()}개")
    print(f"  엣지 수: {G.number_of_edges()}개")
    print(f"  평균 연결도: {sum(dict(G.degree()).values()) / G.number_of_nodes():.2f}")

    # 노드 타입별 통계
    node_types = defaultdict(int)
    for node, data in G.nodes(data=True):
        node_types[data.get('node_type', 'unknown')] += 1

    print(f"\n[노드 타입별 개수]")
    for node_type, count in node_types.items():
        print(f"  {node_type}: {count}개")

    # 가장 중심적인 노드 (PageRank)
    pagerank = nx.pagerank(G)
    top_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:10]

    print(f"\n[가장 영향력 있는 노드 TOP 10 (PageRank)]")
    for node, score in top_nodes:
        node_data = G.nodes[node]
        label = node_data.get('label', node)
        node_type = node_data.get('node_type', 'unknown')
        print(f"  {label} ({node_type}): {score:.4f}")

    # 가장 많은 연결을 가진 Factor
    factors = [(n, G.degree(n)) for n, d in G.nodes(data=True) if d.get('node_type') == 'factor']
    top_factors = sorted(factors, key=lambda x: x[1], reverse=True)[:5]

    print(f"\n[가장 많이 연결된 Factor TOP 5]")
    for node, degree in top_factors:
        label = G.nodes[node].get('label', node)
        print(f"  {label}: {degree}개 연결")

    # 가장 많은 연결을 가진 KPI
    kpis = [(n, G.degree(n)) for n, d in G.nodes(data=True) if d.get('node_type') == 'kpi']
    top_kpis = sorted(kpis, key=lambda x: x[1], reverse=True)[:5]

    print(f"\n[가장 많이 연결된 KPI TOP 5]")
    for node, degree in top_kpis:
        label = G.nodes[node].get('label', node)
        print(f"  {label}: {degree}개 연결")


def main():
    """메인 함수"""

    print("=" * 80)
    print("Step 8: Graph 생성 및 시각화")
    print("=" * 80)
    print()

    # 집계 데이터 로드
    aggregated_path = f"{PROCESSED_DIR}/kpi_factors_aggregated.json"

    if not os.path.exists(aggregated_path):
        print(f"[ERROR] {aggregated_path} 파일을 찾을 수 없습니다.")
        print("먼저 08_aggregate_kpi_factors.py를 실행해주세요.")
        return

    print(f"데이터 로드 중: {aggregated_path}")
    with open(aggregated_path, 'r', encoding='utf-8') as f:
        aggregated_data = json.load(f)

    print(f"  총 관계: {len(aggregated_data['all_relations'])}개")
    print(f"  유니크 KPI: {len(aggregated_data['summary']['unique_kpis'])}개")
    print(f"  유니크 Factor: {len(aggregated_data['summary']['unique_factors'])}개")
    print()

    # 그래프 생성
    print("그래프 생성 중...")
    G, node_stats, edge_stats = create_graph_from_data(aggregated_data)
    print(f"  [OK] 노드 {G.number_of_nodes()}개, 엣지 {G.number_of_edges()}개 생성")
    print()

    # 그래프 분석
    analyze_graph(G)
    print()

    # 시각화 생성
    print("=" * 80)
    print("인터랙티브 시각화 생성 중...")
    html_output = f"{PROCESSED_DIR}/kpi_factor_graph.html"
    create_interactive_visualization(G, html_output)
    print()

    # GraphML 저장
    print("Graph RAG용 데이터 저장 중...")
    graphml_output = f"{PROCESSED_DIR}/kpi_factor_graph.graphml"
    export_for_graph_rag(G, graphml_output)
    print()

    print("=" * 80)
    print("완료!")
    print("=" * 80)
    print(f"\n[생성된 파일]")
    print(f"  1. {html_output}")
    print(f"     브라우저에서 열어 인터랙티브 그래프를 확인하세요")
    print(f"  2. {graphml_output}")
    print(f"     Graph RAG 구현에 사용할 수 있습니다")
    print()


if __name__ == "__main__":
    main()
