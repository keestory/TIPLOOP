/* 첫 로그인 코치마크 투어 (8a) — 홈 위에 딤을 깔고 요소를 하나씩 형광 링으로 짚는다.
   검색 → 카테고리 → 반응 → 글쓰기. 각 스텝 건너뛰기 가능, 마지막은 "첫 글 쓰기".
   완료/건너뛰기 시 서버에 has_seen_tour 저장(다시 안 뜸). */
(function () {
  "use strict";

  var DEFS = [
    { sel: '[data-tour="search"]', n: "1 / 4", title: "여기서 팁·질문을 검색해요",
      body: "탐색에서 원하는 주제를 바로 찾을 수 있어요." },
    { sel: '[data-tour="category"]', n: "2 / 4", title: "관심 카테고리로 걸러 봐요",
      body: "팁·레퍼런스·질문·회고로 피드를 좁혀요." },
    { sel: '[data-tour="react"], .hero, .tapcard', n: "3 / 4",
      title: "도움된 글엔 💡 도움됐어요 · 가볍게 ♥ 공감",
      body: "글을 열면 도움됐어요와 공감을 남길 수 있어요." },
    { sel: '[data-tour="write"]', n: "4 / 4", title: "여기서 나만의 팁을 남겨요",
      body: "시작해볼까요?", cta: "첫 글 쓰기 ✏️", href: "/posts/new" }
  ];

  var steps = DEFS
    .map(function (s) { s.el = document.querySelector(s.sel); return s; })
    .filter(function (s) { return s.el; });
  if (!steps.length) return;

  var i = 0;
  var mask = el("div", "tour-mask");
  var spot = el("div", "tour-spot");
  var pop = el("div", "tour-pop");
  var seen = false;

  function el(tag, cls) { var e = document.createElement(tag); e.className = cls; return e; }

  function markSeen() {
    if (seen) return;
    seen = true;
    try { fetch("/tour/seen", { method: "POST" }); } catch (e) { /* noop */ }
  }

  function close() {
    markSeen();
    [mask, spot, pop].forEach(function (e) { if (e.parentNode) e.parentNode.removeChild(e); });
    window.removeEventListener("resize", place);
  }

  function place() {
    var s = steps[i];
    var r = s.el.getBoundingClientRect();
    var pad = 6;
    spot.style.top = (r.top - pad) + "px";
    spot.style.left = (r.left - pad) + "px";
    spot.style.width = (r.width + pad * 2) + "px";
    spot.style.height = (r.height + pad * 2) + "px";

    // 타깃이 화면 위쪽이면 아래에, 아래쪽이면 위에 말풍선을 둔다.
    var below = r.top < window.innerHeight / 2;
    pop.style.visibility = "hidden";
    pop.style.top = "0px";
    requestAnimationFrame(function () {
      var ph = pop.offsetHeight;
      var top = below ? (r.bottom + 12) : (r.top - ph - 12);
      top = Math.max(12, Math.min(top, window.innerHeight - ph - 12));
      pop.style.top = top + "px";
      pop.style.visibility = "visible";
    });
  }

  function render() {
    var s = steps[i];
    var last = i === steps.length - 1;
    pop.innerHTML = "";
    var step = el("span", "step"); step.textContent = s.n;
    var h = document.createElement("h4"); h.textContent = s.title;
    var p = document.createElement("p"); p.textContent = s.body;
    var row = el("div", "tour-row");
    var skip = el("button", "tour-skip"); skip.type = "button"; skip.textContent = "건너뛰기";
    skip.onclick = close;
    var next = el("button", "tour-next" + (last ? " lime" : ""));
    next.type = "button";
    next.textContent = last ? (s.cta || "완료") : "다음 →";
    next.onclick = function () {
      if (last) {
        markSeen();
        if (s.href) { window.location.href = s.href; return; }
        close();
      } else {
        i += 1;
        steps[i].el.scrollIntoView({ block: "center", behavior: "smooth" });
        setTimeout(function () { render(); place(); }, 260);
      }
    };
    row.appendChild(skip); row.appendChild(next);
    pop.appendChild(step); pop.appendChild(h); pop.appendChild(p); pop.appendChild(row);
  }

  document.body.appendChild(mask);
  document.body.appendChild(spot);
  document.body.appendChild(pop);
  window.addEventListener("resize", place);
  // 첫 스텝 타깃을 화면에 보이게 한 뒤 배치
  steps[0].el.scrollIntoView({ block: "center", behavior: "auto" });
  setTimeout(function () { render(); place(); }, 120);
})();
