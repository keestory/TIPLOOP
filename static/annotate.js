/* 이미지 주석 에디터 — 캔버스에 펜·화살표·사각형·형광펜으로 표시.
   프레임워크 없음. 저장 시 이미지+주석을 하나의 PNG로 합친다(flatten). */
(function () {
  class Annotator {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.img = null;
      this.actions = [];
      this.cur = null;
      this.tool = "pen";
      this.color = "#c8ff00";
      this._bind();
    }

    setImage(image) {
      this.img = image;
      const maxW = 680;
      const scale = Math.min(1, maxW / image.width);
      this.canvas.width = Math.round(image.width * scale);
      this.canvas.height = Math.round(image.height * scale);
      this.actions = [];
      this.redraw();
    }

    reset() { this.img = null; this.actions = []; this.cur = null; }
    setTool(t) { this.tool = t; }
    setColor(c) { this.color = c; }
    undo() { this.actions.pop(); this.redraw(); }
    clearMarks() { this.actions = []; this.redraw(); }
    hasImage() { return !!this.img; }
    toBlob(cb) { this.canvas.toBlob(cb, "image/png"); }

    _pos(e) {
      const r = this.canvas.getBoundingClientRect();
      const p = e.touches ? e.touches[0] : e;
      return {
        x: (p.clientX - r.left) * (this.canvas.width / r.width),
        y: (p.clientY - r.top) * (this.canvas.height / r.height),
      };
    }

    _bind() {
      const down = (e) => {
        if (!this.img) return;
        e.preventDefault();
        const p = this._pos(e);
        this.cur = { tool: this.tool, color: this.color, points: [p], start: p, end: p };
      };
      const move = (e) => {
        if (!this.cur) return;
        e.preventDefault();
        const p = this._pos(e);
        this.cur.points.push(p);
        this.cur.end = p;
        this.redraw();
        this._draw(this.cur);
      };
      const up = () => {
        if (!this.cur) return;
        this.actions.push(this.cur);
        this.cur = null;
        this.redraw();
      };
      this.canvas.addEventListener("mousedown", down);
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
      this.canvas.addEventListener("touchstart", down, { passive: false });
      this.canvas.addEventListener("touchmove", move, { passive: false });
      window.addEventListener("touchend", up);
    }

    redraw() {
      const c = this.ctx;
      c.clearRect(0, 0, this.canvas.width, this.canvas.height);
      if (this.img) c.drawImage(this.img, 0, 0, this.canvas.width, this.canvas.height);
      for (const a of this.actions) this._draw(a);
    }

    _draw(a) {
      const c = this.ctx;
      c.save();
      c.strokeStyle = a.color;
      c.fillStyle = a.color;
      c.lineJoin = "round";
      c.lineCap = "round";
      if (a.tool === "pen") { c.lineWidth = 3; this._path(a.points); }
      else if (a.tool === "highlighter") { c.globalAlpha = 0.35; c.lineWidth = 18; this._path(a.points); }
      else if (a.tool === "rect") { c.lineWidth = 3; c.strokeRect(a.start.x, a.start.y, a.end.x - a.start.x, a.end.y - a.start.y); }
      else if (a.tool === "arrow") { c.lineWidth = 3; this._arrow(a.start, a.end); }
      c.restore();
    }

    _path(pts) {
      const c = this.ctx;
      c.beginPath();
      c.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) c.lineTo(pts[i].x, pts[i].y);
      c.stroke();
    }

    _arrow(s, e) {
      const c = this.ctx;
      c.beginPath();
      c.moveTo(s.x, s.y);
      c.lineTo(e.x, e.y);
      c.stroke();
      const ang = Math.atan2(e.y - s.y, e.x - s.x);
      const h = 16;
      c.beginPath();
      c.moveTo(e.x, e.y);
      c.lineTo(e.x - h * Math.cos(ang - Math.PI / 6), e.y - h * Math.sin(ang - Math.PI / 6));
      c.lineTo(e.x - h * Math.cos(ang + Math.PI / 6), e.y - h * Math.sin(ang + Math.PI / 6));
      c.closePath();
      c.fill();
    }
  }
  window.Annotator = Annotator;
})();
