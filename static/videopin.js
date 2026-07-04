/* 영상 지점 코멘트 — 재생 중 특정 시각+위치에 핀+코멘트 (Frame.io식).
   핀은 항상 클릭 가능. '지점 코멘트 달기'를 켜면 영상 위를 클릭해 새 코멘트를 남긴다. */
(function () {
  const root = document.getElementById("vp");
  if (!root) return;
  const postId = root.dataset.post;
  const canComment = root.dataset.canComment === "1";
  const video = document.getElementById("vp-video");
  const overlay = document.getElementById("vp-overlay");
  const list = document.getElementById("vp-list");
  const toggle = document.getElementById("vp-toggle");

  let comments = [];
  try { comments = JSON.parse(document.getElementById("vp-data").textContent) || []; } catch (e) {}

  const fmt = (t) => {
    t = Math.max(0, Math.floor(t));
    return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0");
  };

  let bubble = null;
  function showBubble(c) {
    if (bubble) bubble.remove();
    bubble = document.createElement("div");
    bubble.className = "vp-bubble";
    bubble.style.left = c.x * 100 + "%";
    bubble.style.top = c.y * 100 + "%";
    const s = document.createElement("strong");
    s.textContent = (c.author_name || "") + " · " + fmt(c.t);
    const b = document.createElement("span");
    b.textContent = c.body;
    bubble.append(s, b);
    overlay.appendChild(bubble);
    setTimeout(() => { if (bubble) { bubble.remove(); bubble = null; } }, 4500);
  }

  function addPin(c) {
    const pin = document.createElement("button");
    pin.type = "button";
    pin.className = "vp-pin";
    pin.style.left = c.x * 100 + "%";
    pin.style.top = c.y * 100 + "%";
    pin.title = c.body;
    pin.addEventListener("click", (e) => {
      e.stopPropagation();
      video.currentTime = c.t; video.pause(); showBubble(c);
    });
    overlay.appendChild(pin);
  }

  function addListItem(c) {
    const li = document.createElement("li");
    li.className = "vp-item";
    const seek = document.createElement("button");
    seek.type = "button"; seek.className = "vp-seek"; seek.textContent = "▶ " + fmt(c.t);
    seek.addEventListener("click", () => { video.currentTime = c.t; video.pause(); showBubble(c); });
    const au = document.createElement("span"); au.className = "vp-au"; au.textContent = c.author_name || "";
    const bd = document.createElement("span"); bd.className = "vp-bd"; bd.textContent = c.body;
    li.append(seek, au, bd);
    list.appendChild(li);
  }

  const render = (c) => { addPin(c); addListItem(c); };
  comments.forEach(render);

  if (!canComment) return;

  let adding = false;
  let draft = null;
  toggle.addEventListener("click", () => {
    adding = !adding;
    overlay.classList.toggle("adding", adding);
    toggle.classList.toggle("is-active", adding);
    toggle.textContent = adding ? "✓ 클릭해서 코멘트 (끄기)" : "➕ 지점 코멘트 달기";
    if (adding) video.pause();
    if (!adding && draft) { draft.remove(); draft = null; }
  });

  overlay.addEventListener("click", (e) => {
    if (!adding || e.target !== overlay) return;
    if (draft) draft.remove();
    const r = overlay.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top) / r.height;
    const t = video.currentTime;
    video.pause();

    draft = document.createElement("div");
    draft.className = "vp-draft";
    draft.style.left = x * 100 + "%";
    draft.style.top = y * 100 + "%";
    const time = document.createElement("div");
    time.className = "vp-draft-time"; time.textContent = fmt(t) + " 지점";
    const ta = document.createElement("textarea"); ta.rows = 2; ta.placeholder = "이 지점에 코멘트";
    const actions = document.createElement("div"); actions.className = "vp-draft-actions";
    const save = document.createElement("button"); save.type = "button"; save.className = "btn btn-small"; save.textContent = "남기기";
    const cancel = document.createElement("button"); cancel.type = "button"; cancel.className = "anno-op"; cancel.textContent = "취소";
    actions.append(save, cancel);
    draft.append(time, ta, actions);
    overlay.appendChild(draft);
    ta.focus();

    cancel.addEventListener("click", () => { draft.remove(); draft = null; });
    save.addEventListener("click", async () => {
      const body = ta.value.trim();
      if (!body) return;
      save.disabled = true;
      const fd = new URLSearchParams();
      fd.set("t", t); fd.set("x", x); fd.set("y", y); fd.set("body", body);
      try {
        const res = await fetch("/posts/" + postId + "/media-comments", { method: "POST", body: fd });
        if (!res.ok) { const j = await res.json().catch(() => ({})); alert(j.error || "저장 실패"); save.disabled = false; return; }
        const j = await res.json();
        render({ id: j.id, t: j.t, x: j.x, y: j.y, body: j.body, author_name: j.author_name });
        draft.remove(); draft = null;
      } catch (err) { alert("저장 실패: " + (err.message || err)); save.disabled = false; }
    });
  });
})();
