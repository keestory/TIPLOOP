# 왜 사람들은 지식을 공유하는가 — 논문 근거와 기능 설계

> 목적: "공유하고 싶은 근본 동기"를 문헌에서 찾아, 그 동기가 **자동으로 충족되도록**
> 티핑의 기능을 설계한다. (동기 → 기능 매핑)

## 문헌이 말하는 핵심 동기

온라인 실무 커뮤니티(electronic networks/communities of practice)의 지식 기여 동기는
반복적으로 아래로 수렴한다.

| 동기 | 설명 | 근거 |
|------|------|------|
| **평판·전문성 인정 (reputation/image)** | "내가 이걸 안다"를 남에게 보이고 직업적 평판을 쌓는다. 공개 네트워크에서 **가장 강한 동기**. | Wasko & Faraj (2005); Kankanhalli et al. (2005) |
| **지식 자기효능감 (self-efficacy/competence)** | "내 지식이 쓸모 있다"는 유능감. 내 글이 실제로 도움됐다는 피드백이 핵심. | Kankanhalli et al. (2005) |
| **돕는 즐거움 (enjoyment in helping)** | 이타적 만족. 남을 돕는 것 자체가 보상. | Wasko & Faraj (2005) |
| **호혜 (reciprocity)** | 받은 만큼 갚는 일반화된 의무감. **기여의 양보다 질·재방문**에 더 작용. | Chen & Hung (2010) 등 |
| **소속·정체성 (belonging/relatedness)** | 커뮤니티에 소속되고 자기 정체성을 확인. | 사회자본 이론 |
| **기록·자기발전 (write-to-learn)** | 쓰면서 내 생각이 정리되고, 내 지식 자산이 쌓인다. | 자기결정이론(SDT) 계열 |

## 가장 중요한 발견 (설계에 직접 반영)

Wasko & Faraj(2005)의 핵심: 사람들은 **평판이 올라간다고 느낄 때, 경험이 있을 때,
네트워크에 구조적으로 엮여 있을 때** 기여한다. 그리고 **놀랍게도 "호혜 기대(내가 주면
남도 주겠지)"나 높은 헌신은 기여량과 무관**했다.

> **함의:** "주면 받는다" 식의 잠금·보상 장치보다, **기여가 곧 평판이 되고, 내 지식이
> 실제로 누군가를 도왔다는 구체적 신호를 주는 것**이 훨씬 강한 레버다.

## 동기 → 티핑 기능 매핑

### 1) 평판 (이미 일부 있음 → 강화)
- 프로필의 **받은 공감 합계(카르마)** ✅ 이미 있음
- **주간/분야별 기여 랭킹**, "이번 주 많이 저장된 팁", 직군별 인기 작성자
- **배지/레벨** (예: "결제 분야 상위 기여자"), 프로필의 임팩트 지표

### 2) 자기효능감 — *가장 저평가된 강력 레버*
- **저장(북마크) + "N명이 저장" 노출** → 작성자에게 "내 지식이 실제로 쓰인다" 신호
- **질문 "채택(해결됨)"** → 답변자에게 강한 유능감 신호
- 프로필 임팩트: "내 글이 저장된 횟수 · 채택된 답변 수"

### 3) 돕는 즐거움
- **"답변 기다리는 질문"** 피드(내 직군 기준)로 도울 기회를 눈앞에
- "당신의 답변이 3명에게 도움이 됐어요" 피드백
- 질문자가 남기는 가벼운 **감사 표시**

### 4) 기록·자기발전 (진입장벽 낮추기)
- **비공개 초안/메모** → 나중에 공개. "일단 나를 위해 기록, 준비되면 공유"
- 내 글을 **콜렉션/시리즈**로 묶어 개인 아카이브처럼

### 5) 소속
- 직군/업종 **홈 피드**를 "내 사람들의 공간"처럼, 주간 다이제스트

## 추천 우선순위 (근거 강도 × 구현 용이성)

1. **저장(북마크) + 저장 수 노출** — 평판·자기효능감·호혜 넛지를 한 번에. 이미 있는
   공감/카르마와 자연스럽게 붙고, 실무자들이 흔히 원하는 기능.
2. **질문 채택(해결됨) + 프로필 임팩트 지표** — 질문 카테고리의 자기효능감을 완성.
3. **"답변 기다리는 질문" 피드** — 돕는 즐거움을 트리거.

> 문헌 근거상 **저장/채택/도움 신호(자기효능감)** 가 "보상·잠금"보다 우선이다.
> "give-to-get" 유료·잠금 장치는 근거가 약하므로 지양.

## 출처
- Wasko & Faraj (2005), *Why Should I Share? Examining Social Capital and Knowledge
  Contribution in Electronic Networks of Practice*, MIS Quarterly —
  https://aisel.aisnet.org/misq/vol29/iss1/4/
- Chen & Hung (2010), *Why do you return the favor... motivations of reciprocity* —
  https://www.sciencedirect.com/science/article/abs/pii/S0747563216303314
- Zhang et al., *Knowledge sharing motivations in online health communities* —
  https://www.sciencedirect.com/science/article/abs/pii/S0747563217303989
- *It is what one does: Why people participate and help others in electronic
  communities of practice* — https://www.researchgate.net/publication/222703124
