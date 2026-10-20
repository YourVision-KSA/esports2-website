/* Arena Night motion (docs/frontend.md rev 3.1 motion spec).
   Vanilla JS, no dependencies. Everything respects prefers-reduced-motion.
   The page works fully without this file (progressive enhancement). */
(function () {
  "use strict";
  var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- countdown: ticks toward [data-countdown] (ISO date). Absent = "--". */
  var cd = document.querySelector("[data-countdown]");
  if (cd) {
    var target = Date.parse(cd.getAttribute("data-countdown"));
    var cells = {
      d: cd.querySelector("[data-cd=d]"),
      h: cd.querySelector("[data-cd=h]"),
      m: cd.querySelector("[data-cd=m]"),
      s: cd.querySelector("[data-cd=s]"),
    };
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    var tick = function () {
      var left = target - Date.now();
      if (isNaN(left) || left < 0) left = 0;
      var sec = Math.floor(left / 1000);
      if (cells.d) cells.d.textContent = String(Math.floor(sec / 86400));
      if (cells.h) cells.h.textContent = pad(Math.floor((sec % 86400) / 3600));
      if (cells.m) cells.m.textContent = pad(Math.floor((sec % 3600) / 60));
      if (cells.s) cells.s.textContent = pad(sec % 60);
    };
    tick();
    setInterval(tick, 1000);
  }

  if (!("IntersectionObserver" in window)) return;

  /* ---- section reveals: .reveal rises+fades on first entry. */
  if (!still) {
    var ro = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -60px 0px" });
    document.querySelectorAll(".reveal").forEach(function (el) { ro.observe(el); });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
  }

  /* ---- stats count-up: [data-count] animates 0 -> value on first view. */
  var co = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      co.unobserve(e.target);
      var el = e.target;
      var end = parseInt(el.getAttribute("data-count"), 10);
      if (isNaN(end) || still) { el.textContent = el.getAttribute("data-count"); return; }
      var t0 = performance.now(), dur = 1100;
      (function step(now) {
        var k = Math.min((now - t0) / dur, 1);
        el.textContent = String(Math.round(end * (1 - Math.pow(1 - k, 3))));
        if (k < 1) requestAnimationFrame(step);
      })(t0);
    });
  }, { threshold: 0.6 });
  document.querySelectorAll("[data-count]").forEach(function (el) { co.observe(el); });
})();
