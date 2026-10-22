/* Live bracket (docs/routes.md → /bracket/<game>/, cut-list item 5).

   Progressive enhancement: the page is complete without this file. With it, the page
   polls the edge-cached JSON (/api/bracket/<slug>.json, 10 s at Cloudflare) and patches
   the cells in place — no reload, no layout jump.

   Load rules (keep the origin quiet and the phone cool):
   - every 15 s while the tab is visible; paused when hidden, immediate poll on return
   - on network/server errors: back off 30 s → 60 s → 120 s, reset on success
   - once the final has a winner: slow down to 60 s
   Arabic labels arrive through data-* attributes (CLAUDE.md rule 1: no Arabic in JS). */
(function () {
  "use strict";
  var root = document.querySelector("[data-bracket-live]");
  if (!root || !window.fetch) return;

  var BASE = 15000;
  var SLOW = 60000;
  var MAX_BACKOFF = 120000;
  var api = root.getAttribute("data-api");
  var labels = { pending: root.getAttribute("data-pending"), forfeit: root.getAttribute("data-forfeit") };
  var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var badge = root.querySelector(".bracket-live");
  var champion = root.querySelector("[data-champion]");
  var delay = BASE;
  var timer = null;
  var inFlight = false;

  function setText(el, value) {
    if (!el || el.textContent === value) return false;
    el.textContent = value;
    return true;
  }

  // Scores like "3–1" sit in an LTR <bdi> so the dash never flips; labels are plain RTL text.
  function setStatus(st, status, text) {
    if (st.textContent === text && st.className === "st st-" + status) return false;
    st.className = "st st-" + status;
    st.textContent = "";
    if (status === "done") {
      var b = document.createElement("bdi");
      b.dir = "ltr";
      b.textContent = text;
      st.appendChild(b);
    } else {
      st.textContent = text;
    }
    return true;
  }

  function flash(cell) {
    if (still) return;
    cell.classList.remove("updated");
    void cell.offsetWidth; // restart the CSS animation
    cell.classList.add("updated");
  }

  function apply(data) {
    var finalRound = 0;
    var champ = "";
    (data.matches || []).forEach(function (m) {
      if (m.round > finalRound) {
        finalRound = m.round;
        champ = m.winner || "";
      }
      var cell = root.querySelector('[data-match="' + m.round + "-" + m.slot + '"]');
      if (!cell) return;
      var p1 = cell.querySelector('[data-f="p1"]');
      var p2 = cell.querySelector('[data-f="p2"]');
      var st = cell.querySelector('[data-f="status"]');
      // empty slot → "winner of M<n>" placeholder rendered by the server (data-ph1/2)
      var changed = setText(p1, m.p1 || cell.getAttribute("data-ph1") || "—");
      changed = setText(p2, m.p2 || cell.getAttribute("data-ph2") || "—") || changed;
      p1.classList.toggle("win", !!m.winner && m.winner === m.p1);
      p2.classList.toggle("win", !!m.winner && m.winner === m.p2);
      p1.classList.toggle("tbd", !m.p1);
      p2.classList.toggle("tbd", !m.p2);
      // these classes drive the bracket connectors (lit once a result / player is in)
      cell.classList.toggle("done", m.status !== "pending");
      cell.classList.toggle("has1", !!m.p1);
      cell.classList.toggle("has2", !!m.p2);
      var text = m.status === "pending" ? labels.pending : m.status === "forfeit" ? labels.forfeit : m.score || "";
      changed = setStatus(st, m.status, text) || changed;
      if (changed) flash(cell);
    });
    if (champion) {
      setText(champion.querySelector('[data-f="champion"]'), champ);
      champion.hidden = !champ;
    }
    return !!champ;
  }

  function schedule(ms) {
    clearTimeout(timer);
    if (!document.hidden) timer = setTimeout(poll, ms);
  }

  function poll() {
    if (inFlight || document.hidden) return;
    inFlight = true;
    fetch(api, { headers: { Accept: "application/json" }, cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function (data) {
        var finished = apply(data);
        delay = BASE;
        if (badge) badge.hidden = false;
        schedule(finished ? SLOW : BASE);
      })
      .catch(function () {
        delay = Math.min(Math.max(delay * 2, 30000), MAX_BACKOFF);
        schedule(delay);
      })
      .then(function () {
        inFlight = false;
      });
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) clearTimeout(timer);
    else poll(); // coming back to the tab: refresh straight away
  });
  if (badge) badge.hidden = false;
  schedule(BASE);
})();
