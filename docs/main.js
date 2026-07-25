/* hivemind docs — interaction + the hero memory-trace graph.
   All effects degrade gracefully and respect prefers-reduced-motion. */
(() => {
  "use strict";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- nav: scrolled state + active section ---- */
  const nav = document.querySelector(".nav");
  const onScroll = () => nav && nav.classList.toggle("scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const navLinks = [...document.querySelectorAll(".nav-links a[href^='#']")];
  const linkFor = (id) => navLinks.find((a) => a.getAttribute("href") === "#" + id);
  const sections = [...document.querySelectorAll("main section[id]")];
  if ("IntersectionObserver" in window && sections.length) {
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          navLinks.forEach((a) => a.classList.remove("active"));
          const link = linkFor(e.target.id);
          if (link) link.classList.add("active");
        });
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: 0 }
    );
    sections.forEach((s) => spy.observe(s));
  }

  /* ---- scroll reveal ---- */
  const reveals = [...document.querySelectorAll(".reveal")];
  if (reduceMotion || !("IntersectionObserver" in window)) {
    reveals.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            obs.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.12 }
    );
    reveals.forEach((el) => io.observe(el));
  }

  /* ---- copy buttons ---- */
  document.querySelectorAll(".copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const code = btn.parentElement.querySelector("pre code, pre");
      if (!code) return;
      const text = code.innerText.replace(/\n$/, "");
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); } catch {}
        ta.remove();
      }
      const label = btn.textContent;
      btn.textContent = "copied";
      btn.classList.add("done");
      setTimeout(() => {
        btn.textContent = label;
        btn.classList.remove("done");
      }, 1600);
    });
  });

  /* ---- reference: tabbed layout + detail pane ---- */
  const refTabs = [...document.querySelectorAll(".ref-tab")];
  const refPanels = [...document.querySelectorAll(".ref-panel")];
  const refDetail = document.getElementById("refDetail");

  if (refDetail && refTabs.length) {
    const detailName = refDetail.querySelector(".ref-detail-name");
    const detailDesc = refDetail.querySelector(".ref-detail-desc");
    const allChips = [...document.querySelectorAll(".ref-panel code[data-desc]")];

    const clearSelection = () => {
      allChips.forEach((c) => c.classList.remove("active"));
      refDetail.classList.remove("has-selection");
      if (detailName) detailName.textContent = "";
      if (detailDesc) detailDesc.textContent = "";
    };

    const selectChip = (chip) => {
      if (chip.classList.contains("active")) { clearSelection(); return; }
      allChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      refDetail.classList.add("has-selection");
      if (detailName) detailName.textContent = chip.textContent;
      if (detailDesc) detailDesc.textContent = chip.dataset.desc;
    };

    allChips.forEach((chip) => {
      chip.setAttribute("role", "button");
      chip.setAttribute("tabindex", "0");
      chip.addEventListener("click", () => selectChip(chip));
      chip.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectChip(chip); }
      });
    });

    refTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        refTabs.forEach((t) => { t.classList.remove("active"); t.setAttribute("aria-selected", "false"); });
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");
        const targetId = tab.getAttribute("aria-controls");
        refPanels.forEach((p) => {
          if (p.id === targetId) { p.hidden = false; p.classList.add("active"); }
          else { p.hidden = true; p.classList.remove("active"); }
        });
        clearSelection();
      });
    });
  }

  /* ---- hero memory-trace graph ---- */
  const canvas = document.getElementById("graph");
  if (!canvas || reduceMotion) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const COLORS = ["#ff2a33", "#e7000b", "#ff6b5e"];
  let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
  let nodes = [];
  let raf = 0, t = 0;

  function size() {
    const r = canvas.getBoundingClientRect();
    w = r.width; h = r.height;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.floor(w * dpr));
    canvas.height = Math.max(1, Math.floor(h * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function build() {
    const count = Math.max(22, Math.min(54, Math.round((w * h) / 26000)));
    nodes = Array.from({ length: count }, (_, i) => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.12,
      vy: (Math.random() - 0.5) * 0.12,
      r: 1.4 + Math.random() * 2.6,
      // "learned utility": some nodes are strong (bright) attractors
      base: Math.random() * 0.5 + (Math.random() < 0.22 ? 0.5 : 0.05),
      phase: Math.random() * Math.PI * 2,
      speed: 0.4 + Math.random() * 0.9,
      c: COLORS[i % COLORS.length],
    }));
  }

  const LINK = 132; // edge distance threshold

  function frame() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);

    // edges first
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d2 = dx * dx + dy * dy;
        if (d2 > LINK * LINK) continue;
        const d = Math.sqrt(d2);
        const strength = 1 - d / LINK;
        ctx.strokeStyle = "rgba(96,180,210," + (strength * 0.22).toFixed(3) + ")";
        ctx.lineWidth = strength * 1.1;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }

    // nodes
    for (const n of nodes) {
      n.x += n.vx; n.y += n.vy;
      if (n.x < -20) n.x = w + 20; else if (n.x > w + 20) n.x = -20;
      if (n.y < -20) n.y = h + 20; else if (n.y > h + 20) n.y = -20;

      // utility pulse — traces strengthen and fade
      const pulse = 0.5 + 0.5 * Math.sin(t * n.speed + n.phase);
      const lum = Math.min(1, n.base + pulse * 0.45);
      const r = n.r * (0.85 + lum * 0.6);

      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 5);
      grad.addColorStop(0, n.c);
      grad.addColorStop(1, "transparent");
      ctx.globalAlpha = 0.12 + lum * 0.5;
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r * 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.globalAlpha = 0.5 + lum * 0.5;
      ctx.fillStyle = n.c;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    raf = requestAnimationFrame(frame);
  }

  function start() {
    size();
    build();
    cancelAnimationFrame(raf);
    frame();
  }

  let resizeT = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(start, 180);
  });

  // pause when the hero is offscreen (perf)
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { if (!raf) frame(); }
        else { cancelAnimationFrame(raf); raf = 0; }
      });
    }, { threshold: 0 }).observe(canvas);
  }

  start();
})();
