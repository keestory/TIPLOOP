/* 공유 카드 — 인스타 스토리용 짧은 모션 카드를 순수 Canvas 2D로 그려서
   영상(webm)으로 녹화하거나, 지원 안 되는 기기에서는 정지 이미지(PNG)로
   폴백한다. 외부 라이브러리 없음 — html2canvas 등을 쓰지 않고 캔버스에
   직접 그려서 어디서나 안정적으로 동작하게 한다.

   레이아웃: 720x1280(9:16). 배경 드리프트 글로우는 애니메이션 내내 흐르고,
   숫자 카운트업 → 헤드라인 → 서브텍스트 → 푸터 순으로 등장한다. */
(function () {
  "use strict";

  var specEl = document.getElementById("share-spec");
  if (!specEl) return;
  var spec = JSON.parse(specEl.textContent);

  var canvas = document.getElementById("share-canvas");
  var W = 720, H = 1280;
  var DPR = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = W * DPR;
  canvas.height = H * DPR;
  var ctx = canvas.getContext("2d");
  ctx.scale(DPR, DPR);

  var DURATION = 2600; // ms — 전체 애니메이션 길이

  function clamp01(x) { return Math.max(0, Math.min(1, x)); }
  function easeOutCubic(x) { return 1 - Math.pow(1 - x, 3); }

  function roundRect(c, x, y, w, h, r) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  function wrapText(c, text, x, y, maxWidth, lineHeight, maxLines) {
    maxLines = maxLines || 3;
    var words = String(text || "").split(/\s+/).filter(Boolean);
    var lines = [];
    var line = "";
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + " " + words[i] : words[i];
      if (c.measureText(test).width > maxWidth && line) {
        lines.push(line);
        line = words[i];
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      var last = lines[maxLines - 1];
      while (c.measureText(last + "…").width > maxWidth && last.length > 1) {
        last = last.slice(0, -1);
      }
      lines[maxLines - 1] = last + "…";
    }
    lines.forEach(function (ln, idx) { c.fillText(ln, x, y + idx * lineHeight); });
    return lines.length;
  }

  var BLOBS = [
    { cx: 0.18, cy: 0.16, r: 230, speed: 0.00026, phase: 0 },
    { cx: 0.86, cy: 0.28, r: 190, speed: 0.00021, phase: 2.1 },
    { cx: 0.32, cy: 0.86, r: 260, speed: 0.00019, phase: 4.2 },
  ];

  function drawBlobs(c, t) {
    BLOBS.forEach(function (b) {
      var x = b.cx * W + Math.sin(t * b.speed + b.phase) * 44;
      var y = b.cy * H + Math.cos(t * b.speed * 1.3 + b.phase) * 44;
      var grad = c.createRadialGradient(x, y, 0, x, y, b.r);
      grad.addColorStop(0, "rgba(205,255,71,0.32)");
      grad.addColorStop(1, "rgba(205,255,71,0)");
      c.fillStyle = grad;
      c.beginPath();
      c.arc(x, y, b.r, 0, Math.PI * 2);
      c.fill();
    });
  }

  function draw(c, t) {
    c.clearRect(0, 0, W, H);
    c.fillStyle = "#1A1917";
    c.fillRect(0, 0, W, H);
    drawBlobs(c, t);

    // 브랜드 마크
    c.save();
    c.globalAlpha = clamp01(t / 250);
    c.fillStyle = "#FCFBF8";
    c.font = "800 34px 'Gothic A1', sans-serif";
    c.fillText("TIPLOOP", 56, 96);
    var bw = c.measureText("TIPLOOP").width;
    c.fillStyle = "#CDFF47";
    c.beginPath(); c.arc(56 + bw + 14, 87, 6, 0, Math.PI * 2); c.fill();
    c.restore();

    // 이어보 태그
    c.save();
    c.globalAlpha = clamp01((t - 80) / 250);
    c.font = "700 24px 'IBM Plex Mono', monospace";
    var eyebrow = spec.eyebrow || "";
    var padX = 18;
    var tw = c.measureText(eyebrow).width;
    var pillW = tw + padX * 2, pillH = 44;
    roundRect(c, 56, 130, pillW, pillH, pillH / 2);
    c.fillStyle = "#CDFF47";
    c.fill();
    c.fillStyle = "#1A1917";
    c.textBaseline = "middle";
    c.fillText(eyebrow, 56 + padX, 130 + pillH / 2 + 1);
    c.textBaseline = "alphabetic";
    c.restore();

    // 큰 숫자 카운트업
    var numT = clamp01((t - 150) / 1000);
    var current = Math.round((spec.big || 0) * easeOutCubic(numT));
    c.save();
    c.globalAlpha = clamp01((t - 150) / 200);
    c.fillStyle = "#CDFF47";
    c.font = "900 188px 'Gothic A1', sans-serif";
    c.fillText(String(current), 54, 560);
    c.restore();

    c.save();
    c.globalAlpha = clamp01((t - 150) / 200);
    c.fillStyle = "#FCFBF8";
    c.font = "700 38px 'IBM Plex Sans KR', sans-serif";
    c.fillText(spec.unit || "", 58, 622);
    c.restore();

    // 헤드라인 (슬라이드업 + 페이드)
    var hlT = clamp01((t - 1150) / 350);
    c.save();
    c.globalAlpha = hlT;
    c.translate(0, (1 - hlT) * 18);
    c.fillStyle = "#FCFBF8";
    c.font = "700 46px 'Gothic A1', sans-serif";
    wrapText(c, spec.headline || "", 58, 750, W - 116, 56, 3);
    c.restore();

    // 서브텍스트
    var subT = clamp01((t - 1550) / 300);
    if (spec.sub) {
      c.save();
      c.globalAlpha = subT * 0.8;
      c.fillStyle = "#C7C1B2";
      c.font = "500 30px 'IBM Plex Sans KR', sans-serif";
      c.fillText(spec.sub, 58, H - 158);
      c.restore();
    }

    // 푸터
    var footT = clamp01((t - 1850) / 300);
    c.save();
    c.globalAlpha = footT;
    c.fillStyle = "#8A8578";
    c.font = "600 26px 'IBM Plex Mono', monospace";
    c.fillText("tiploop.vercel.app", 58, H - 66);
    c.restore();
  }

  function playOnce(onDone) {
    var startTime = null;
    function loop(now) {
      if (startTime === null) startTime = now;
      var t = now - startTime;
      draw(ctx, t);
      if (t < DURATION) requestAnimationFrame(loop);
      else if (onDone) onDone();
    }
    requestAnimationFrame(loop);
  }

  // 폰트 로딩을 기다렸다가(최대 800ms) 프리뷰 자동 재생
  var fontsReady = (document.fonts && document.fonts.ready) ? document.fonts.ready : Promise.resolve();
  Promise.race([fontsReady, new Promise(function (r) { setTimeout(r, 800); })]).then(function () {
    playOnce();
  });

  function exportImage() {
    return new Promise(function (resolve) {
      draw(ctx, DURATION); // 완성된 마지막 프레임 상태로 정지컷 캡처
      canvas.toBlob(function (blob) { resolve(blob); }, "image/png");
    });
  }

  function exportVideo() {
    if (!canvas.captureStream || typeof MediaRecorder === "undefined") {
      return Promise.resolve(null);
    }
    var stream;
    try { stream = canvas.captureStream(30); } catch (e) { return Promise.resolve(null); }

    var candidates = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
    var mime = candidates.filter(function (m) {
      return MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(m);
    })[0];
    var recorder;
    try { recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream); }
    catch (e) { return Promise.resolve(null); }

    var chunks = [];
    recorder.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
    var done = new Promise(function (resolve) {
      recorder.onstop = function () {
        resolve(chunks.length ? new Blob(chunks, { type: recorder.mimeType || "video/webm" }) : null);
      };
      recorder.onerror = function () { resolve(null); };
    });
    // timeslice를 줘서 dataavailable이 주기적으로 흐르게 한다(끝에 한 번만 몰아 나오는 걸 방지)
    try { recorder.start(250); } catch (e) { return Promise.resolve(null); }
    playOnce(function () { try { recorder.stop(); } catch (e) { /* 이미 멈췄으면 무시 */ } });
    return done;
  }

  function fileName(ext) { return "tipping-" + spec.kind + "." + ext; }

  var MIN_VIDEO_BYTES = 3000; // 이보다 작으면 헤더만 있는 빈 영상으로 보고 이미지로 폴백

  function buildFile(preferVideo) {
    var attempt = preferVideo ? exportVideo() : Promise.resolve(null);
    return attempt.then(function (blob) {
      if (blob && blob.size >= MIN_VIDEO_BYTES) {
        return new File([blob], fileName("webm"), { type: blob.type });
      }
      return exportImage().then(function (png) {
        return new File([png], fileName("png"), { type: "image/png" });
      });
    });
  }

  function downloadFile(file) {
    var url = URL.createObjectURL(file);
    var a = document.createElement("a");
    a.href = url; a.download = file.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  var hint = document.getElementById("share-hint");

  function doShare(button, labelEl, preferVideo) {
    var original = labelEl.textContent;
    button.disabled = true;
    labelEl.textContent = "만드는 중…";
    hint.textContent = "";
    buildFile(preferVideo).then(function (file) {
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        return navigator.share({ files: [file], title: "TIPLOOP", text: spec.headline || "TIPLOOP" });
      }
      downloadFile(file);
      hint.textContent = "파일을 저장했어요. 인스타그램 스토리에서 직접 올려주세요.";
    }).catch(function (e) {
      if (!(e && e.name === "AbortError")) {
        hint.textContent = "공유에 실패했어요. 이미지로 저장을 눌러보세요.";
      }
    }).finally(function () {
      button.disabled = false;
      labelEl.textContent = original;
    });
  }

  document.getElementById("share-btn").addEventListener("click", function () {
    doShare(this, document.getElementById("share-btn-label"), true);
  });
  document.getElementById("save-btn").addEventListener("click", function () {
    doShare(this, document.getElementById("save-btn-label"), false);
  });
})();
