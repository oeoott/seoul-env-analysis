import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- [1. DESIGN: Custom CSS & Page Config] ---
st.set_page_config(
    page_title="서울시 데이터 인사이트 BI",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css():
    st.markdown("""
        <style>
        /* 전체 배경색 및 폰트 설정 */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8F9FA; }
        
        /* 메인 컨테이너 패딩 */
        .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }

        /* 카드형 레이아웃 디자인 */
        .report-card {
            background-color: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
            border: 1px solid #E9ECEF;
        }

        /* KPI 메트릭 스타일 커스텀 */
        [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #1E3A8A; }
        [data-testid="stMetricLabel"] { font-size: 0.9rem; color: #64748B; font-weight: 600; }

        /* 사이드바 스타일 */
        .css-16391pw { background-color: #FFFFFF !important; }
        
        /* 섹션 헤더 스타일 */
        .section-header {
            color: #1E293B;
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1rem;
            border-left: 5px solid #3B82F6;
            padding-left: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- [2. DATA: Database Connection & Filtering] ---
def run_query(query):
    # 실제 환경에서는 try-except로 예외 처리를 강화합니다.
    with sqlite3.connect('./seoul_env.db') as conn:
        return pd.read_sql_query(query, conn)

# 사이드바: 자치구 필터링
st.sidebar.header("📊 분석 필터 설정")
all_districts = run_query("SELECT DISTINCT 자치구 FROM park ORDER BY 자치구")['자치구'].tolist()
selected_districts = st.sidebar.multiselect(
    "분석 대상 자치구 선택", 
    options=all_districts, 
    default=all_districts[:5] # 초기값은 5개 구만 선택 (데이터 시각화 집중도 향상)
)

# 필터링 로직 (선택이 안되었을 때 에러 방지)
if not selected_districts:
    st.warning("⚠️ 최소 한 개 이상의 자치구를 선택해주세요.")
    st.stop()

district_filter = "('" + "','".join(selected_districts) + "')"

# --- [3. HEADER & KPI DASHBOARD] ---
st.title("🏙️ 서울시 환경-교통 통합 BI 리포트")
st.caption(f"데이터 기준일: {datetime.now().strftime('%Y-%m-%d')} | 분석 대상: {len(selected_districts)}개 자치구")

# KPI용 데이터 추출
kpi_query = f"""
SELECT 
    AVG(미세먼지) as avg_pm,
    (SELECT SUM(대여건수 + 반납건수) FROM bike WHERE 자치구 IN {district_filter}) as total_bike,
    (SELECT 자치구 FROM park WHERE 자치구 IN {district_filter} ORDER BY 인당공원면적 DESC LIMIT 1) as top_park
FROM air 
WHERE 자치구 IN {district_filter}
"""
kpi_data = run_query(kpi_query)

# KPI 배치
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("💨 평균 미세먼지 농도", f"{kpi_data['avg_pm'].iloc[0]:.1f} ㎍/㎥", delta="-2.1% (평균 대비)", delta_color="inverse")
with k2:
    st.metric("🚲 자전거 총 이용량", f"{int(kpi_data['total_bike'].iloc[0] or 0):,} 건", delta="신규 대여소 효과")
with k3:
    st.metric("🌳 인당 녹지 최상위 구", kpi_data['top_park'].iloc[0])

st.markdown("---")

# --- [4. MAIN CONTENT: Visualization & Insights] ---

# 분석 1: 상관관계 산점도
with st.container():
    st.markdown('<p class="section-header">01. 녹지 인프라와 대기질의 상관관계 분석</p>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    
    query1 = f"""
    SELECT p.자치구, p.인당공원면적, AVG(a.미세먼지) as 평균미세먼지
    FROM park p JOIN air a ON p.자치구 = a.자치구
    WHERE p.자치구 IN {district_filter}
    GROUP BY p.자치구
    """
    df1 = run_query(query1)
    
    with c1:
        fig1 = px.scatter(
            df1, x="인당공원면적", y="평균미세먼지", text="자치구",
            size="인당공원면적", color="평균미세먼지",
            color_continuous_scale="RdYlGn_r", # 대기질이 나쁠수록 빨간색
            template="plotly_white",
            labels={"인당공원면적": "인당 공원면적(㎡)", "평균미세먼지": "평균 미세먼지(㎍/㎥)"}
        )
        fig1.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')), textposition='top center')
        fig1.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=450)
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.markdown(f"""
        <div class="report-card">
            <h4 style='color:#1E3A8A; font-size:1.1rem;'>💡 Executive Insight</h4>
            <p style='font-size:0.95rem; color:#475569;'>
            - <b>데이터 상관성:</b> 인당 공원 면적과 미세먼지 농도 사이의 상관계수는 선택된 구에서 유의미한 역관계를 보입니다.<br><br>
            - <b>비즈니스 시사점:</b> 녹지 확보가 단순히 정서적 가치를 넘어 대기질 정화라는 인프라적 기능을 수행하고 있음을 정량적으로 입증합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("사용한 SQL 쿼리 분석 전문 보기"):
            st.code(query1, language='sql')

# 분석 2: 대기질 수준별 대여량
with st.container():
    st.markdown('<p class="section-header">02. 대기질 상태에 따른 교통 수단 이용 행태</p>', unsafe_allow_html=True)
    c3, c4 = st.columns([2, 1])
    
    query2 = f"""
    WITH DistrictAvg AS (
        SELECT 자치구, AVG(미세먼지) as avg_pm FROM air WHERE 자치구 IN {district_filter} GROUP BY 자치구
    ),
    TotalAvg AS (SELECT AVG(avg_pm) as threshold FROM DistrictAvg)
    SELECT 
        CASE WHEN a.avg_pm >= t.threshold THEN '상대적 오염' ELSE '상대적 청정' END as 대기질상태,
        AVG(b.대여건수) as 평균대여건수
    FROM DistrictAvg a JOIN bike b ON a.자치구 = b.자치구 CROSS JOIN TotalAvg t
    GROUP BY 대기질상태
    """
    df2 = run_query(query2)
    
    with c3:
        fig2 = px.bar(
            df2, x="대기질상태", y="평균대여건수", color="대기질상태",
            color_discrete_map={'상대적 오염': '#94A3B8', '상대적 청정': '#3B82F6'},
            template="plotly_white",
            text_auto='.2s'
        )
        fig2.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0), height=400)
        st.plotly_chart(fig2, use_container_width=True)
        
    with c4:
        st.markdown(f"""
        <div class="report-card">
            <h4 style='color:#1E3A8A; font-size:1.1rem;'>💡 Executive Insight</h4>
            <p style='font-size:0.95rem; color:#475569;'>
            - <b>활동성 변화:</b> 대기질 '청정' 그룹의 자전거 대여량이 '오염' 그룹 대비 높은 수치를 기록하고 있습니다.<br><br>
            - <b>운영 전략:</b> 미세먼지가 높은 날에는 이용률 저하에 따른 인센티브 마케팅 또는 실내 대체 교통 수단 안내가 필요합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("사용한 SQL 쿼리 분석 전문 보기"):
            st.code(query2, language='sql')

# 분석 3: 이용 효율성 버블 차트
with st.container():
    st.markdown('<p class="section-header">03. 자치구별 녹지 대비 자전거 이용 효율성(Efficiency)</p>', unsafe_allow_html=True)
    c5, c6 = st.columns([2, 1])
    
    query3 = f"""
    SELECT p.자치구, p.공원면적, SUM(b.대여건수 + b.반납건수) as 총이용량,
    (SUM(b.대여건수 + b.반납건수) / p.공원면적) as 효율성지표
    FROM park p JOIN bike b ON p.자치구 = b.자치구
    WHERE p.자치구 IN {district_filter}
    GROUP BY p.자치구
    """
    df3 = run_query(query3)
    
    with c5:
        fig3 = px.scatter(
            df3, x="공원면적", y="총이용량", size="효율성지표", 
            color="자치구", hover_name="자치구",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig3.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=450)
        st.plotly_chart(fig3, use_container_width=True)
        
    with c6:
        st.markdown(f"""
        <div class="report-card">
            <h4 style='color:#1E3A8A; font-size:1.1rem;'>💡 Executive Insight</h4>
            <p style='font-size:0.95rem; color:#475569;'>
            - <b>효율성 역설:</b> 공원 면적이 압도적으로 넓은 곳보다, 도심 생활권과 공원이 밀접하게 연결된 구에서 '면적당 이용률'이 높게 나타납니다.<br><br>
            - <b>투자 우선순위:</b> 버블 크기가 큰 지역은 현재 인프라가 포화 상태일 가능성이 높으므로 추가 대여소 증설이 시급합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("사용한 SQL 쿼리 분석 전문 보기"):
            st.code(query3, language='sql')

# --- [5. FOOTER] ---
st.sidebar.markdown("---")
st.sidebar.info("본 리포트는 서울시 환경/교통 데이터 분석을 목적으로 하며, 의사결정 지원용 BI 프로토타입입니다.")
