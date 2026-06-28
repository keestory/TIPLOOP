# 프론트엔드 가이드

## 대시보드 (Streamlit 기반)

이 프로젝트의 UI는 Streamlit으로 구축된 모니터링 대시보드입니다.

### 구조
```
ui/
├── app.py              # 메인 엔트리포인트
├── pages/
│   ├── dashboard.py    # 에이전트 실행 현황
│   ├── quality.py      # 품질 스코어 보드
│   └── tasks.py        # 태스크 관리
└── components/
    ├── agent_card.py   # 에이전트 상태 카드
    └── metric_chart.py # 메트릭 차트
```

### 실행
```bash
streamlit run ui/app.py
```

## 컨벤션
- 컴포넌트는 순수 함수로 작성
- 상태 관리는 `st.session_state` 사용
- 데이터 처리는 Service 레이어에 위임
