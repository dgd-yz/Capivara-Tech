/* Capivara Tech — interactions (vanilla, no framework) */
(function () {
  "use strict";

  /* ----- animated flow-field background ----- */
  function initBackground() {
    var cv = document.getElementById("ct-bg");
    if (!cv || cv.dataset.init) return;
    cv.dataset.init = "1";
    var ctx = cv.getContext("2d");
    if (!ctx) return;
    var prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var w, h, dpr;
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = cv.clientWidth; h = cv.clientHeight;
      cv.width = w * dpr; cv.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);
    if (prefersReduced) return;

    var colors = ["rgba(217,137,63,", "rgba(192,83,59,", "rgba(234,160,90,", "rgba(201,160,106,", "rgba(168,99,52,"];
    var N = Math.max(220, Math.min(620, Math.floor((w * h) / 2600)));
    function mk() {
      return {
        x: Math.random() * w, y: Math.random() * h,
        c: colors[(Math.random() * colors.length) | 0],
        a: 0.035 + Math.random() * 0.075,
        v: 1.1 + Math.random() * 1.0,
        life: 80 + Math.random() * 240,
      };
    }
    var P = []; for (var i = 0; i < N; i++) P.push(mk());

    function field(x, y, t) {
      return (Math.sin(x * 0.0024 + t) +
        Math.cos(y * 0.0029 - t * 0.8) +
        Math.sin((x + y) * 0.0015 + t * 0.55) +
        Math.cos((x - y) * 0.0019 - t * 0.4)) * 1.25;
    }

    function draw(time) {
      var t = time * 0.00016;
      var pulse = (Math.sin(time * 0.0004) + 1) * 0.5;
      ctx.fillStyle = "rgba(21,17,13,0.05)";
      ctx.fillRect(0, 0, w, h);
      ctx.lineCap = "round";
      ctx.lineWidth = 1.15;
      for (var k = 0; k < P.length; k++) {
        var p = P[k];
        var ang = field(p.x, p.y, t);
        var nx = p.x + Math.cos(ang) * p.v;
        var ny = p.y + Math.sin(ang) * p.v;
        ctx.strokeStyle = p.c + (p.a * (0.55 + pulse * 0.6)) + ")";
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(nx, ny);
        ctx.stroke();
        p.x = nx; p.y = ny; p.life -= 1;
        if (p.life < 0 || p.x < -12 || p.x > w + 12 || p.y < -12 || p.y > h + 12) {
          var m = mk(); p.x = m.x; p.y = m.y; p.c = m.c; p.a = m.a; p.v = m.v; p.life = m.life;
        }
      }
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
  }

  /* ----- cursor glow ----- */
  function initGlow() {
    var glow = document.getElementById("ct-glow");
    if (!glow || glow.dataset.init) return;
    glow.dataset.init = "1";
    var tx = window.innerWidth / 2, ty = window.innerHeight / 2, cx = tx, cy = ty;
    window.addEventListener("mousemove", function (e) { tx = e.clientX; ty = e.clientY; });
    (function tick() {
      cx += (tx - cx) * 0.12; cy += (ty - cy) * 0.12;
      glow.style.transform = "translate(" + cx + "px," + cy + "px)";
      requestAnimationFrame(tick);
    })();
  }

  /* ----- scroll progress bar ----- */
  function initProgress() {
    var bar = document.getElementById("ct-progress");
    if (!bar || bar.dataset.init) return;
    bar.dataset.init = "1";
    function onScroll() {
      var sc = document.scrollingElement || document.documentElement;
      var max = sc.scrollHeight - sc.clientHeight;
      bar.style.width = (max > 0 ? (sc.scrollTop / max) * 100 : 0) + "%";
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ----- reveal on scroll ----- */
  function initReveals() {
    var els = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
    if (!("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("is-in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); }
      });
    }, { threshold: 0, rootMargin: "0px 0px -10% 0px" });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ----- animated counters ----- */
  function initCounters() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-count]"));
    function animate(el) {
      var raw = el.getAttribute("data-count");
      var m = raw.match(/(\D*)(\d+)(\D*)/);
      if (!m) { el.textContent = raw; return; }
      var prefix = m[1], target = parseInt(m[2], 10), suffix = m[3];
      var dur = 1400, start = performance.now();
      (function step(now) {
        var p = Math.min((now - start) / dur, 1);
        var ease = 1 - Math.pow(1 - p, 3);
        el.textContent = prefix + Math.round(target * ease) + suffix;
        if (p < 1) requestAnimationFrame(step);
      })(start);
    }
    if (!("IntersectionObserver" in window)) { nodes.forEach(animate); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { animate(en.target); io.unobserve(en.target); }
      });
    }, { threshold: 0.5 });
    nodes.forEach(function (n) { io.observe(n); });
  }

  /* ----- mobile nav burger ----- */
  function initNav() {
    var burger = document.getElementById("ct-burger");
    var links = document.getElementById("ct-nav-links");
    if (!burger || !links || burger.dataset.init) return;
    burger.dataset.init = "1";
    burger.addEventListener("click", function () {
      burger.classList.toggle("is-open");
      links.classList.toggle("is-open");
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") { burger.classList.remove("is-open"); links.classList.remove("is-open"); }
    });
  }

  /* ----- schedule day tabs ----- */
  function initTabs() {
    var tabs = Array.prototype.slice.call(document.querySelectorAll(".ct-tab[data-day]"));
    if (!tabs.length) return;
    tabs.forEach(function (tab) {
      if (tab.dataset.init) return;
      tab.dataset.init = "1";
      tab.addEventListener("click", function () {
        var day = tab.getAttribute("data-day");
        tabs.forEach(function (t) { t.classList.toggle("is-active", t === tab); });
        document.querySelectorAll(".ct-day").forEach(function (panel) {
          panel.classList.toggle("is-active", panel.getAttribute("data-day") === day);
        });
      });
    });
  }

  /* ----- speakers carousel (o CSS só aplica o layout de carrossel no celular) ----- */
  function initSpeakerCarousel() {
    var track = document.querySelector("#palestrantes .ct-grid-4");
    if (!track || track.dataset.carousel) return;
    var slides = Array.prototype.slice.call(track.querySelectorAll(".ct-speaker"));
    if (slides.length < 2) return;
    track.dataset.carousel = "1";

    var mq = window.matchMedia("(max-width: 600px)");
    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var chevron = function (d) {
      return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + d + '"/></svg>';
    };
    var current = -1;

    track.classList.add("is-carousel");
    track.setAttribute("role", "region");
    track.setAttribute("aria-roledescription", "carrossel");
    track.setAttribute("aria-label", "Palestrantes e instrutores");
    slides.forEach(function (s, i) {
      s.setAttribute("role", "group");
      s.setAttribute("aria-roledescription", "slide");
      s.setAttribute("aria-label", (i + 1) + " de " + slides.length);
    });

    var controls = document.createElement("div");
    controls.className = "ct-carousel__controls";
    controls.innerHTML =
      '<div class="ct-carousel__ui">' +
        '<button type="button" class="ct-carousel__btn" data-dir="-1" aria-label="Palestrante anterior">' + chevron("M15 5l-7 7 7 7") + "</button>" +
        '<div class="ct-carousel__status" aria-live="polite"><b></b> / ' + slides.length + "</div>" +
        '<button type="button" class="ct-carousel__btn" data-dir="1" aria-label="Próximo palestrante">' + chevron("M9 5l7 7-7 7") + "</button>" +
      "</div>" +
      '<div class="ct-carousel__bar" aria-hidden="true"><span></span></div>';
    track.parentNode.insertBefore(controls, track.nextSibling);
    var prev = controls.querySelector('[data-dir="-1"]');
    var next = controls.querySelector('[data-dir="1"]');
    var counter = controls.querySelector(".ct-carousel__status b");
    var bar = controls.querySelector(".ct-carousel__bar");

    /* "Ler mais": bios longas ficam recortadas no celular */
    var mores = [];
    slides.forEach(function (s) {
      var q = s.querySelector(".q");
      if (!q) return;
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "ct-more"; btn.hidden = true;
      btn.textContent = "Ler mais"; btn.setAttribute("aria-expanded", "false");
      q.parentNode.appendChild(btn);
      btn.addEventListener("click", function () { setOpen(s, !s.classList.contains("is-open")); });
      mores.push({ slide: s, q: q, btn: btn });
    });
    function setOpen(slide, open) {
      slide.classList.toggle("is-open", open);
      mores.forEach(function (m) {
        if (m.slide !== slide) return;
        m.btn.textContent = open ? "Ler menos" : "Ler mais";
        m.btn.setAttribute("aria-expanded", open ? "true" : "false");
      });
      if (!open) updateMore();
    }
    function updateMore() {
      mores.forEach(function (m) {
        if (!mq.matches) { m.slide.classList.remove("is-open"); m.btn.hidden = true; return; }
        if (m.slide.classList.contains("is-open")) { m.btn.hidden = false; return; }
        m.btn.hidden = !(m.q.scrollHeight > m.q.clientHeight + 1);
      });
    }

    function nearest() {
      var mid = track.scrollLeft + track.clientWidth / 2, best = 0, bestDist = Infinity;
      slides.forEach(function (s, i) {
        var d = Math.abs(s.offsetLeft + s.offsetWidth / 2 - mid);
        if (d < bestDist) { bestDist = d; best = i; }
      });
      return best;
    }
    function setActive(i) {
      if (i === current) return;
      if (current > -1) setOpen(slides[current], false);
      current = i;
      slides.forEach(function (s, k) { s.classList.toggle("is-active", k === i); });
      counter.textContent = i + 1;
      bar.style.setProperty("--p", ((i + 1) / slides.length * 100) + "%");
      prev.disabled = i === 0;
      next.disabled = i === slides.length - 1;
    }
    function goTo(i) {
      i = Math.max(0, Math.min(slides.length - 1, i));
      var s = slides[i];
      var left = s.offsetLeft + s.offsetWidth / 2 - track.clientWidth / 2;
      if (track.scrollTo) track.scrollTo({ left: left, behavior: reduced ? "auto" : "smooth" });
      else track.scrollLeft = left;
    }

    var ticking = false;
    track.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; setActive(nearest()); });
    }, { passive: true });
    prev.addEventListener("click", function () { goTo(current - 1); });
    next.addEventListener("click", function () { goTo(current + 1); });
    track.addEventListener("keydown", function (e) {
      if (!mq.matches) return;
      if (e.key === "ArrowRight") { e.preventDefault(); goTo(current + 1); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); goTo(current - 1); }
      else if (e.key === "Home") { e.preventDefault(); goTo(0); }
      else if (e.key === "End") { e.preventDefault(); goTo(slides.length - 1); }
    });

    function sync() {
      if (mq.matches) track.setAttribute("tabindex", "0"); else track.removeAttribute("tabindex");
      setActive(nearest());
      updateMore();
    }
    var resizeTimer;
    window.addEventListener("resize", function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(sync, 120); });
    if (mq.addEventListener) mq.addEventListener("change", sync); else if (mq.addListener) mq.addListener(sync);
    window.addEventListener("load", sync);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(sync);
    sync();
  }

  function init() {
    initBackground();
    initGlow();
    initProgress();
    initReveals();
    initCounters();
    initNav();
    initTabs();
    initSpeakerCarousel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
