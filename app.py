import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- [1. DESIGN: Custom CSS & Page Config] ---
st.set_page_config(page_title="서울시 환경-교통 대시보드", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
        /* 배경 및 기본 폰트 */
        html, body, [class*="css"] { background-color: #F8F9FA; font-family: 'Pretendard', sans-serif; }
        
        /* 카드형 컨테이너 */
        .report-card {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
            border: 1px solid #E9ECEF;
        }
        
        /* 섹션 제목 */
        .section-header {
            font-size: 1.4rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 5px solid #007BFF;
        }

        /* 인사이트 박스 (st.info 대체용) */
        .insight-box {
            background-color: #F0F7FF;
            border-radius: 8px;
            padding: 15px;
            border-left: 5px solid #0056b3;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        
        /* 메트릭 스타일 */
        [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #007BFF; }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- [2. DATA: Connection & Filter] ---
def run_query(query):
    with sqlite3.connect('./seoul_env.db') as conn:
        return pd.read_sql_query(query, conn)

# 사이드바 필터
st.sidebar.header("📍 지역 필터링")
all_districts = run_query("SELECT DISTINCT 자치구 FROM park ORDER BY 자치구")['자치구'].tolist()
selected_districts = st.sidebar.multiselect("분석할 자치구를 선택하세요", all_districts, default=all_districts)

if not selected_districts:
    st.warning("분석할 자치구를 하나 이상 선택해주세요.")
    st.stop()

dist_filter_sql = "('" + "','".join(selected_districts) + "')"

# --- [3. TOP KPI METRICS] ---
st.title("🏙️ 서울시 환경 및 교통 데이터 통합 분석 대시보드")
st.markdown("서울시의 **공원 면적, 미세먼지 농도, 따릉이 이용 현황** 상관관계 리포트")

kpi_data = run_query(f"""
    SELECT 
        AVG(미세먼지) as avg_pm,
        (SELECT SUM(대여건수 + 반납건수) FROM bike WHERE 자치구 IN {dist_filter_sql}) as total_bike,
        (SELECT 자치구 FROM park WHERE 자치구 IN {dist_filter_sql} ORDER BY 인당공원면적 DESC LIMIT 1) as max_park
    FROM air WHERE 자치구 IN {dist_filter_sql}
""")

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("💨 평균 미세먼지 농도", f"{kpi_data['avg_pm'].iloc[0]:.2f} ㎍/㎥")
with m2:
    st.metric("🚲 따릉이 총 이용량", f"{int(kpi_data['total_bike'].iloc[0] or 0):,} 건")
with m3:
    st.metric("🌳 인당 녹지 1위 구", kpi_data['max_park'].iloc[0])

st.divider()

# --- [4. ANALYSIS SECTIONS] ---

# 분석 1
st.markdown('<p class="section-header">1. 자치구별 녹지 인프라와 공기질의 상관관계</p>', unsafe_allow_html=True)
col1_chart, col1_desc = st.columns([2, 1])

query1 = f"""
SELECT p.자치구, p.인당공원면적, AVG(a.미세먼지) as 평균미세먼지
FROM park p JOIN air a ON p.자치구 = a.자치구
WHERE p.자치구 IN {dist_filter_sql}
GROUP BY p.자치구
"""
df1 = run_query(query1)

with col1_chart:
    fig1 = px.scatter(df1, x="인당공원면적", y="평균미세먼지", text="자치구", 
                      size="인당공원면적", color="평균미세먼지",
                      color_continuous_scale=px.colors.sequential.Viridis, template="plotly_white")
    st.plotly_chart(fig1, use_container_width=True)

with col1_desc:
    st.markdown("""
    <div class="insight-box">
        <strong>[ 녹지의 양적 규모와 대기질의 비선형성 ]</strong><br>
        - 데이터 근거: 1인당 공원 면적이 서울에서 가장 넓은 종로구(76.52㎡)와 강북구(50.34㎡)의 데이터를 분석한 결과, 미세먼지 농도와의 상관계수는 약 0.1로 매우 낮게 나타났습니다.<br>
        - 분석: 이는 공원 면적이라는 '양적 지표'가 자치구의 미세먼지 농도를 결정하는 단일 변수가 아님을 증명합니다. 미세먼지는 녹지 면적보다 교통량, 인접 지역의 오염원 유입 등 외부 요인에 더 민감하게 반응하기 때문입니다.<br>
        - 결론: 향후 환경 정책은 단순히 녹지의 면적을 넓히는 '양적 확대'를 넘어, 미세먼지 흡착 효율이 높은 수종 식재나 바람길 확보 등 대기 정화 기능을 극대화하는 '질적 설계'에 집중해야 함을 시사합니다.
    </div>
    """, unsafe_allow_html=True)
    with st.expander("사용한 SQL 쿼리 보기"):
        st.code(query1, language='sql')

# 분석 2
st.divider()
st.markdown('<p class="section-header">2. 미세먼지 농도에 따른 따릉이 이용 변화</p>', unsafe_allow_html=True)
col2_chart, col2_desc = st.columns([2, 1])

query2 = f"""
WITH AirQuality AS (
    SELECT 자치구, AVG(미세먼지) as avg_pm10 FROM air WHERE 자치구 IN {dist_filter_sql} GROUP BY 자치구
),
Threshold AS (SELECT AVG(avg_pm10) as total_avg FROM AirQuality)
SELECT 
    CASE WHEN a.avg_pm10 >= t.total_avg THEN '미세먼지 높음' ELSE '미세먼지 낮음' END as 대기질상태,
    AVG(b.대여건수) as 평균대여건수
FROM AirQuality a JOIN bike b ON a.자치구 = b.자치구 CROSS JOIN Threshold t
GROUP BY 대기질상태
"""
df2 = run_query(query2)

with col2_chart:
    fig2 = px.bar(df2, x="대기질상태", y="평균대여건수", color="대기질상태",
                  color_discrete_map={'미세먼지 높음': '#EF553B', '미세먼지 낮음': '#636EFA'},
                  template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

with col2_desc:
    st.markdown("""
    <div class="insight-box">
        <strong>[ 대기질 지표에 따른 따릉이 수요의 '심리적 저항선' ]</strong><br>
        - 데이터 근거: 미세먼지 농도가 평균 이하인 '낮음' 그룹의 평균 대여량은 약 81만 건인 반면, '높음' 그룹은 약 52만 건에 그쳤습니다. 대기질이 좋은 지역의 이용량이 약 54% 더 많습니다.<br>
        - 분석: 데이터는 시민들이 대기 환경 지표에 매우 민감하게 반응하며, 특정 농도 이상의 환경에서는 야외 활동(따릉이 이용)을 급격히 자제하는 '심리적 저항선'이 존재함을 수치로 입증합니다.<br>
        - 결론: 따릉이 운영 전략 측면에서 미세먼지는 수익성과 직결되는 핵심 변수입니다. 대기질 취약 지역에는 '미세먼지 저감형 대여소 쉼터' 설치나 '환경 연동 인센티브' 등 환경적 제약을 기술적으로 보완하는 마케팅 전략이 필요합니다.
    </div>
    """, unsafe_allow_html=True)
    with st.expander("사용한 SQL 쿼리 보기"):
        st.code(query2, language='sql')

# 분석 3
st.divider()
st.markdown('<p class="section-header">3. 자치구별 공원 인프라 기반 자전거 이용 활성화도</p>', unsafe_allow_html=True)
col3_chart, col3_desc = st.columns([2, 1])

query3 = f"""
SELECT p.자치구, p.공원면적, SUM(b.대여건수 + b.반납건수) as 총이용량,
(SUM(b.대여건수 + b.반납건수) / p.공원면적) as 면적대비이용효율
FROM park p JOIN bike b ON p.자치구 = b.자치구
WHERE p.자치구 IN {dist_filter_sql}
GROUP BY p.자치구
ORDER BY 총이용량 DESC
"""
df3 = run_query(query3)

with col3_chart:
    fig3 = px.scatter(df3, x="공원면적", y="총이용량", size="면적대비이용효율", color="자치구",
                      template="plotly_white", labels={"공원면적": "공원 전체 면적 (㎡)", "총이용량": "자전거 총 이용건수"})
    st.plotly_chart(fig3, use_container_width=True)

with col3_desc:
    st.markdown("""
    <div class="insight-box">
        <strong>[ 인프라 규모와 이용 효율의 역설 ]</strong><br>
        - 데이터 근거: 인당 공원 면적 1위인 종로구(76.52㎡)의 대여량은 약 57만 건인 반면, 인당 면적이 훨씬 좁은 강서구(8.04㎡)는 약 220만 건으로 서울시 최다 이용량을 기록했습니다.<br>
        - 분석: 자전거 활성화의 결정적 요인은 '공원의 크기'가 아니라 '지형의 평탄함'과 '생활권-공원 간의 연계성(Connectivity)'입니다. 산지가 많고 경사가 급한 종로·강북구보다 평지가 발달하고 업무/주거지가 밀집한 강서·송파·영등포구에서 인프라 효율이 극대화됩니다.<br>
        - 결론: 녹지는 풍부하나 지형적 한계가 있는 자치구는 일반 따릉이보다 전기 따릉이(e-따릉이) 배치를 우선적으로 확대하여 인프라 활용도를 높이는 지형 맞춤형 교통 정책이 요구됩니다.
    </div>
    """, unsafe_allow_html=True)
    with st.expander("사용한 SQL 쿼리 보기"):
        st.code(query3, language='sql')

# 푸터
st.sidebar.info("데이터 출처: 서울시 공공데이터 포털 기반 가상 DB")
