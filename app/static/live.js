/* Hooqed live layer for a published hooq (v0). The v7 template is unchanged; this script only
   1) saves the lead when the visitor submits their contact details, 2) records the booking choice,
   3) hides the demo-only notes, 4) loads the owner's calendar link as an iframe straight away. */
(function () {
  var C = window.HOOQED; if (!C) return;
  var leadId = null, pending = [];
  function post(path, body) {
    return fetch(C.api + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body), keepalive: true})
      .then(function (r) { return r.json(); });
  }
  function brief() { try { return window.leadBrief(); } catch (e) { return ""; } }
  var st = document.createElement("style"); st.textContent = "p.demo.hq-off{display:none}"; document.head.appendChild(st);
  function tidy() {
    document.querySelectorAll("p.demo").forEach(function (p) { if (/^\s*Demo/.test(p.textContent)) p.classList.add("hq-off"); });
    var box = document.querySelector(".bk-embed");
    if (box && !box.querySelector("iframe") && !box.classList.contains("iclosed-widget") && !box.dataset.hq) {
      box.dataset.hq = "1";
      var f = document.createElement("iframe"); f.src = box.dataset.url; f.title = box.getAttribute("title") || "Booking calendar";
      f.style.cssText = "width:100%;height:100%;border:0"; box.appendChild(f);
    }
  }
  new MutationObserver(tidy).observe(document.documentElement, {childList: true, subtree: true}); tidy();
  document.addEventListener("submit", function (e) {
    if (!e.target || e.target.id !== "cf") return;
    setTimeout(function () {
      var S = window.__S || {};
      // the v7 brief ends with the booking choice; at this point none is made yet, so that part is replaced
      var b = brief().replace(/, (call|appointment) booked .*$/, ", no time picked yet");
      post("/lead", {name: S.name, phone: S.phone, email: S.email, postcode: S.pc, answers: S.a, brief: b})
        .then(function (r) { leadId = r.id; pending.splice(0).forEach(function (f) { f(); }); });
    }, 0);
  }, true);
  function action(kind) {
    setTimeout(function () {
      var S = window.__S || {}, body = {kind: kind, tab: S.tab, cb: S.cb, brief: brief()};
      var go = function () { post("/lead/" + leadId + "/action", body); };
      if (leadId) go(); else pending.push(go);
    }, 0);
  }
  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("button"); if (!t) return;
    if (t.dataset.confirm) action("confirm");
    else if (t.dataset.textme) action("text-me");
  }, true);
})();
