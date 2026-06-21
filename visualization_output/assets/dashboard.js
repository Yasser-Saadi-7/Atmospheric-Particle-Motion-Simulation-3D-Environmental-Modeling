/* ================================================================
   AtmosphericSimulation — Stage UI-4 Dashboard Script
   Offline-compatible (file://).  No fetch(), no framework.
   All data driven by window.DASHBOARD_MANIFEST (generated_manifest.js).
   ================================================================ */

"use strict";

/* ----------------------------------------------------------------
   Static project data
---------------------------------------------------------------- */
var DASHBOARD_DATA = {
  year: new Date().getFullYear(),

  summaryCards: [
    { label: "Simulation Steps", value: "100,000", sub: "latest simulation step" },
    { label: "Particles",        value: "10,000",  sub: "SPH particles in shell" },
    { label: "Geometry",         value: "3D Spherical Shell", sub: "atmospheric domain" },
    { label: "Generated Outputs", value: "—",      sub: "available artifacts" },
  ],

  timeline: [
    { stage: "Stage 1", range: "0\u201320,000",   title: "Dry Hydrostatic Spin-up",
      desc: "Particles settle into hydrostatic balance with velocity damping. No thermal forcing." },
    { stage: "Stage 2", range: "20,000\u201340,000", title: "Differential Thermal Forcing",
      desc: "Equatorial heating and polar cooling applied. Temperature gradient drives circulation." },
    { stage: "Stage 3", range: "40,000\u201360,000", title: "Planetary Rotation & \u03A8",
      desc: "Coriolis-like rotation introduced. Streamfunction \u03A8 computed as circulation diagnostic." },
    { stage: "Stage 4", range: "60,000\u2013100,000", title: "Moisture Coupling",
      desc: "Humidity q\u209A field, evaporation/condensation physics, and latent heating enabled." },
  ],

  /* ---- B: Main Results ---- */
  mainResults: [
    {
      id: "particle-viewer", icon: "\uD83C\uDF10",
      title: "3D Particle Viewer",
      desc: "Interactive 3D scatter of all particles coloured by temperature, radial velocity, or humidity. Light background for clear visibility.",
      links: [
        { label: "Temperature",  href: "html/particle_3d_temperature.html" },
        { label: "Radial vel.",  href: "html/particle_3d_vr.html" },
        { label: "Humidity q\u209A", href: "html/particle_3d_qp.html" },
      ],
    },
    {
      id: "particle-anim", icon: "\u25B6\uFE0F",
      title: "Particle Animations",
      desc: "Animated evolution of the particle distribution over all saved snapshots, with Play/Pause control.",
      links: [
        { label: "Temperature anim.", href: "html/particle_animation_temperature.html" },
        { label: "Velocity anim.",    href: "html/particle_animation_vr.html" },
        { label: "Preview GIF",      href: "animations/particle_animation_preview.gif" },
      ],
    },
    {
      id: "streamfunction", icon: "\u21BA",
      title: "Streamfunction \u03A8",
      desc: "Latitude\u2013altitude heatmap with contours. Candidate meridional circulation structure — not a proven cell identification.",
      links: [
        { label: "Heatmap (HTML)",   href: "html/streamfunction_heatmap_contours.html" },
        { label: "max|\u03A8| vs time", href: "html/max_abs_psi_vs_time.html" },
        { label: "Preview PNG",      href: "png/streamfunction_heatmap_contours.png" },
      ],
    },
    {
      id: "vtheta", icon: "\u2194\uFE0F",
      title: "Meridional Wind v\u03B8",
      desc: "Mean meridional wind v\u03B8 in latitude\u2013altitude space from binned circulation accumulator.",
      links: [
        { label: "Heatmap (HTML)", href: "html/vtheta_heatmap.html" },
        { label: "Preview PNG",   href: "png/vtheta_heatmap.png" },
      ],
    },
    {
      id: "moisture", icon: "\uD83D\uDCA7",
      title: "Moisture / Stage 4",
      desc: "Specific humidity q\u209A heatmap, water balance diagnostics, evaporation/condensation time series.",
      links: [
        { label: "q\u209A heatmap",     href: "html/humidity_lat_alt_heatmap.html" },
        { label: "Water balance",    href: "html/water_balance_panels.html" },
        { label: "Evap/Cond",        href: "html/evap_cond_timeseries.html" },
      ],
    },
  ],

  /* ---- C: Diagnostics ---- */
  diagnostics: [
    {
      id: "water-balance", icon: "\u2696\uFE0F",
      title: "Water Balance",
      desc: "total_q vs expected_total_q conservation check over simulation time. PASS/WARNING/FAIL from moisture_balance.csv.",
      links: [
        { label: "Panels (HTML)",  href: "html/water_balance_panels.html" },
        { label: "PNG preview",    href: "png/water_balance_panels.png" },
      ],
    },
    {
      id: "evap-cond", icon: "\u2601\uFE0F",
      title: "Evaporation & Condensation",
      desc: "Time series of evaporation and condensation rates, cumulative totals, and latent heating.",
      links: [
        { label: "Timeseries (HTML)", href: "html/evap_cond_timeseries.html" },
        { label: "PNG preview",       href: "png/evap_cond_timeseries.png" },
      ],
    },
    {
      id: "temp-zones", icon: "\uD83C\uDF21\uFE0F",
      title: "Temperature Zones",
      desc: "Mean kinetic temperature by latitude zone (equatorial, mid-latitude, polar) over simulation time.",
      links: [
        { label: "Timeseries (HTML)", href: "html/temperature_zones_timeseries.html" },
        { label: "PNG preview",       href: "png/temperature_zones_timeseries.png" },
      ],
    },
    {
      id: "sim-energy", icon: "\u26A1",
      title: "Simulation Energy",
      desc: "Kinetic, gravitational potential, and total energy from simulation_log.csv.",
      links: [
        { label: "Energy plot (HTML)", href: "html/simulation_energy.html" },
        { label: "PNG preview",        href: "png/simulation_energy.png" },
      ],
    },
  ],

  /* ---- D: Gallery groups ----
   * Each item may have:
   *   src:         primary image path (PNG/GIF)  — shown in <img> if file exists
   *   srcFallback: secondary image path checked if src is missing
   *   href:        interactive HTML to open on click / "Open interactive" button
   *   htmlFallback:if src & srcFallback are missing, show an HTML-link card
   *   hrefOpen:    direct link for "Open original" in lightbox (defaults to src)
   ---- */
  galleryGroups: [
    {
      label: "Stage 3 \u2014 Streamfunction & Circulation",
      items: [
        { title: "Streamfunction Heatmap",  sub: "\u03A8 lat\u2013alt contours",
          src: "png/streamfunction_heatmap_contours.png",
          href: "html/streamfunction_heatmap_contours.html" },
        { title: "max|\u03A8| vs Time",     sub: "Streamfunction amplitude",
          src: "png/max_abs_psi_vs_time.png",
          href: "html/max_abs_psi_vs_time.html" },
        { title: "Meridional Wind v\u03B8", sub: "Lat\u2013alt heatmap",
          src: "png/vtheta_heatmap.png",
          href: "html/vtheta_heatmap.html" },
      ],
    },
    {
      label: "Stage 4 \u2014 Moisture",
      items: [
        { title: "Humidity q\u209A Heatmap", sub: "Specific humidity",
          src: "png/humidity_lat_alt_heatmap.png",
          href: "html/humidity_lat_alt_heatmap.html" },
        { title: "Water Balance",            sub: "Conservation check",
          src: "png/water_balance_panels.png",
          href: "html/water_balance_panels.html" },
        { title: "Evap / Cond",              sub: "Rates over time",
          src: "png/evap_cond_timeseries.png",
          href: "html/evap_cond_timeseries.html" },
      ],
    },
    {
      label: "Stage 2 \u2014 Thermal Diagnostics",
      items: [
        { title: "Temperature Zones",         sub: "Lat zone time series",
          src: "png/temperature_zones_timeseries.png",
          href: "html/temperature_zones_timeseries.html" },
        { title: "Altitude\u2013Temperature", sub: "Profile (mean T per altitude bin)",
          src: "png/altitude_temperature_profile.png",
          href: "html/altitude_temperature_profile.html" },
        { title: "Simulation Energy",         sub: "KE + PE over time",
          src: "png/simulation_energy.png",
          href: "html/simulation_energy.html" },
      ],
    },
    {
      label: "Particle Viewer Previews",
      items: [
        { title: "3D Particles \u2014 Temperature", sub: "2D x\u2013z preview \u00b7 interactive 3D viewer",
          src: "png/particle_preview_temperature.png",
          srcFallback: "png/particle_3d_temperature_preview.png",
          href: "html/particle_3d_temperature.html",
          htmlFallback: "html/particle_3d_temperature.html" },
        { title: "3D Particles \u2014 Velocity",    sub: "Radial velocity v_r \u00b7 2D x\u2013z preview",
          src: "png/particle_preview_vr.png",
          srcFallback: "png/particle_3d_vr_preview.png",
          href: "html/particle_3d_vr.html",
          htmlFallback: "html/particle_3d_vr.html" },
        { title: "Animation Preview",               sub: "Multi-step particle animation",
          src: "animations/particle_animation_preview.gif",
          srcFallback: "animations/particle_animation_preview.png",
          href: "animations/particle_animation_preview.gif",
          htmlFallback: "html/particle_animation_temperature.html",
          extraHref: "html/particle_animation_temperature.html",
          extraLabel: "Open interactive animation \u2192" },
      ],
    },
  ],

  /* ---- E: Export & Documentation ---- */
  exportDocs: [
    {
      id: "paraview", icon: "\uD83D\uDDC4\uFE0F",
      title: "ParaView / VTK Export",
      desc: "Open this .vtk file in ParaView and colour by temperature, q_p, v_r, or v_theta. Scalar arrays embedded as POINT_DATA. Generated from the latest particle snapshot.",
      links: [
        { label: "particles_step_100000.vtk", href: "vtk/particles_step_100000.vtk" },
      ],
    },
    {
      id: "docs", icon: "\uD83D\uDCDA",
      title: "Project Documentation",
      desc: "Physics model report, visualization notes, and Stage UI documentation.",
      links: [
        { label: "README (Stage UI-3)", href: "docs/README_UI_STAGE_3.md" },
        { label: "README (Stage UI-2)", href: "docs/README_UI_STAGE_2.md" },
        { label: "Physics report",     href: "docs/physics_model_report.md" },
      ],
    },
    {
      id: "artifact-summary", icon: "\uD83D\uDCC1",
      title: "Generated File Inventory",
      desc: "Summary of all HTML, PNG, GIF, and VTK files generated by the visualization pipeline.",
      links: [
        { label: "Dashboard summary JSON", href: "summary/dashboard_summary.json" },
        { label: "Missing outputs log",    href: "summary/missing_required_outputs.md" },
      ],
    },
    {
      id: "tech-details", icon: "\u2699\uFE0F",
      title: "Technical Details",
      desc: "Input data folder used by the visualization builder when generating this dashboard.",
      links: [],
    },
  ],
};

/* ----------------------------------------------------------------
   Card → Manifest category mapping (controls badge + button)
---------------------------------------------------------------- */
var CARD_MANIFEST_MAP = {
  "particle-viewer": {
    categories: ["particleViewer"],
    primaryPriority: [
      "html/particle_3d_temperature.html",
      "html/particle_3d_vr.html",
      "html/particle_3d_qp.html",
    ],
    openLabel: "Open 3D viewer",
  },
  "particle-anim": {
    categories: ["particleAnimations"],
    primaryPriority: [
      "html/particle_animation_temperature.html",
      "html/particle_animation_vr.html",
      "animations/particle_animation_preview.gif",
    ],
    openLabel: "Open animation",
  },
  "streamfunction": {
    categories: ["streamfunction"],
    primaryPriority: [
      "html/streamfunction_heatmap_contours.html",
      "html/max_abs_psi_vs_time.html",
      "png/streamfunction_heatmap_contours.png",
    ],
    openLabel: "Open streamfunction",
  },
  "vtheta": {
    categories: ["meridionalWind"],
    primaryPriority: [
      "html/vtheta_heatmap.html",
      "png/vtheta_heatmap.png",
    ],
    openLabel: "Open wind diagnostic",
  },
  "moisture": {
    categories: ["moisture", "waterBalance", "evaporationCondensation"],
    primaryPriority: [
      "html/humidity_lat_alt_heatmap.html",
      "html/particle_3d_qp.html",
      "html/water_balance_panels.html",
      "html/evap_cond_timeseries.html",
      "png/humidity_lat_alt_heatmap.png",
    ],
    openLabel: "Open moisture diagnostic",
  },
  "water-balance": {
    categories: ["waterBalance"],
    primaryPriority: [
      "html/water_balance_panels.html",
      "png/water_balance_panels.png",
    ],
    openLabel: "Open water balance",
  },
  "evap-cond": {
    categories: ["evaporationCondensation"],
    primaryPriority: [
      "html/evap_cond_timeseries.html",
      "png/evap_cond_timeseries.png",
    ],
    openLabel: "Open evap/cond",
  },
  "temp-zones": {
    categories: ["thermalDiagnostics"],
    primaryPriority: [
      "html/temperature_zones_timeseries.html",
      "png/temperature_zones_timeseries.png",
    ],
    openLabel: "Open temperature zones",
  },
  "sim-energy": {
    categories: ["summary"],
    primaryPriority: [
      "html/simulation_energy.html",
      "png/simulation_energy.png",
    ],
    openLabel: "Open energy plot",
  },
  "paraview": {
    categories: ["vtk"],
    primaryPriority: ["vtk/particles_step_100000.vtk"],
    openLabel: "Open VTK file",
  },
  "artifact-summary": {
    categories: ["summary"],
    primaryPriority: [
      "summary/dashboard_summary.json",
      "summary/missing_required_outputs.md",
    ],
    openLabel: "Open summary",
  },
  "docs": {
    categories: ["documentation"],
    primaryPriority: [
      "docs/README_UI_STAGE_3.md",
      "docs/README.md",
      "docs/physics_model_report.md",
    ],
    openLabel: "Open documentation",
  },
  "tech-details": {
    categories: ["summary"],
    primaryPriority: ["summary/dashboard_summary.json"],
    openLabel: "View summary",
  },
};

/* ----------------------------------------------------------------
   Badge helpers
---------------------------------------------------------------- */
function badgeClass(status) {
  var map = {
    pass:            "badge badge-pass",
    warning:         "badge badge-warning",
    fail:            "badge badge-fail",
    pending:         "badge badge-pending",
    planned:         "badge badge-planned",
    available:       "badge badge-available",
    partial:         "badge badge-partial",
    generated:       "badge badge-generated",
    "not-available": "badge badge-not-available",
  };
  return map[status] || "badge badge-pending";
}
function badgeLabel(status) {
  var map = {
    pass:            "PASS",
    warning:         "WARNING",
    fail:            "FAIL",
    pending:         "PENDING",
    planned:         "PLANNED",
    available:       "AVAILABLE",
    partial:         "PARTIAL",
    generated:       "GENERATED",
    "not-available": "N/A",
  };
  return map[status] || status.toUpperCase();
}

/* ----------------------------------------------------------------
   DOM helper
---------------------------------------------------------------- */
function el(tag, attrs) {
  var node = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(function(k) {
      var v = attrs[k];
      if (v === null || v === undefined) return;
      if (k === "className") { node.className = v; }
      else if (k === "textContent") { node.textContent = v; }
      else if (k === "innerHTML") { node.innerHTML = v; }
      else { node.setAttribute(k, v); }
    });
  }
  for (var i = 2; i < arguments.length; i++) {
    var child = arguments[i];
    if (!child) continue;
    if (typeof child === "string") node.appendChild(document.createTextNode(child));
    else node.appendChild(child);
  }
  return node;
}

/* ----------------------------------------------------------------
   Theme toggle
---------------------------------------------------------------- */
var HERO_PREVIEW_CANDIDATES = [
  "png/particle_preview_temperature.png",
  "animations/particle_animation_preview.png",
  "animations/particle_animation_preview.gif",
  "png/particle_3d_temperature_preview.png",
];

function _updateThemeButton(btn, theme) {
  var icon = btn.querySelector(".theme-toggle-icon");
  var isDark = theme === "dark";
  if (icon) icon.textContent = isDark ? "\u2600" : "\u263E";
  var label = isDark ? "Switch to light mode" : "Switch to dark mode";
  btn.setAttribute("aria-label", label);
  btn.setAttribute("title", label);
}

function initThemeToggle() {
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;
  var html = document.documentElement;
  var stored = localStorage.getItem("atmsim-theme");
  if (stored) html.setAttribute("data-theme", stored);
  _updateThemeButton(btn, html.getAttribute("data-theme") || "light");

  btn.addEventListener("click", function() {
    var current = html.getAttribute("data-theme") || "light";
    var next = current === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("atmsim-theme", next);
    _updateThemeButton(btn, next);
  });
}

/* ----------------------------------------------------------------
   Navigation scroll spy (active section highlight)
---------------------------------------------------------------- */
function initNavScrollSpy() {
  var navLinks = Array.prototype.slice.call(
    document.querySelectorAll(".site-nav a[href^='#']")
  );
  if (!navLinks.length) return;

  var sections = navLinks.map(function(a) {
    var id = (a.getAttribute("href") || "").replace("#", "");
    return { id: id, el: document.getElementById(id), link: a };
  }).filter(function(s) { return s.el; });

  function setActive(id) {
    navLinks.forEach(function(a) {
      var match = (a.getAttribute("href") || "") === "#" + id;
      a.classList.toggle("is-active", match);
    });
  }

  if (!("IntersectionObserver" in window)) {
    setActive("overview");
    return;
  }

  var visible = {};
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      visible[entry.target.id] = entry.isIntersecting ? entry.intersectionRatio : 0;
    });
    var bestId = "overview";
    var bestRatio = 0;
    sections.forEach(function(s) {
      var ratio = visible[s.id] || 0;
      if (ratio > bestRatio) {
        bestRatio = ratio;
        bestId = s.id;
      }
    });
    if (bestRatio > 0) setActive(bestId);
  }, { root: null, rootMargin: "-45% 0px -45% 0px", threshold: [0, 0.1, 0.25, 0.5] });

  sections.forEach(function(s) { observer.observe(s.el); });
  setActive("overview");
}

/* ----------------------------------------------------------------
   Lightbox
---------------------------------------------------------------- */
function initLightbox() {
  var overlay  = document.getElementById("lightbox-overlay");
  var img      = document.getElementById("lightbox-img");
  var caption  = document.getElementById("lightbox-caption");
  var actions  = document.getElementById("lightbox-actions");
  var closeBtn = document.getElementById("lightbox-close");
  if (!overlay) return;

  function open(src, title, hrefOrig) {
    img.src = src;
    img.alt = title || "";
    if (caption) caption.textContent = title || "";
    if (actions) {
      actions.innerHTML = "";
      var downBtn = el("a", {
        className: "lb-btn",
        href: src,
        download: "",
        textContent: "\u2193 Download",
      });
      actions.appendChild(downBtn);
      if (hrefOrig && hrefOrig !== src) {
        var openBtn = el("a", {
          className: "lb-btn lb-btn-primary",
          href: hrefOrig,
          target: "_blank",
          rel: "noopener noreferrer",
          textContent: "\u2197 Open original file",
        });
        actions.appendChild(openBtn);
      }
    }
    overlay.classList.add("active");
    overlay.focus();
  }

  function close() {
    overlay.classList.remove("active");
    img.src = "";
  }

  if (closeBtn) closeBtn.addEventListener("click", close);
  overlay.addEventListener("click", function(e) {
    if (e.target === overlay) close();
  });
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape" && overlay.classList.contains("active")) close();
  });

  // Expose so gallery items can call it
  window._openLightbox = open;
}

/* ----------------------------------------------------------------
   Render: Phase timeline
---------------------------------------------------------------- */
function renderTimeline(containerId) {
  var container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";
  DASHBOARD_DATA.timeline.forEach(function(item) {
    var node = el("div", { className: "timeline-item" },
      el("div", { className: "tl-stage", textContent: item.stage }),
      el("div", { className: "tl-title", textContent: item.title }),
      el("div", { className: "tl-range", textContent: "Steps " + item.range }),
      el("div", { className: "tl-desc",  textContent: item.desc })
    );
    container.appendChild(node);
  });
}

/* ----------------------------------------------------------------
   Render: Card grid (Main Results + Diagnostics + Export)
---------------------------------------------------------------- */
function _buildCard(item) {
  var card = el("div", { className: "card", id: item.id });

  // icon + badge row
  var row = el("div", { className: "card-header-row",
    style: "display:flex;align-items:flex-start;justify-content:space-between;gap:0.5rem;margin-bottom:0.5rem;" });
  if (item.icon) row.appendChild(el("div", { className: "card-icon", textContent: item.icon }));
  var badge = el("span", { className: "badge badge-pending", textContent: "PENDING",
    style: "flex-shrink:0;margin-top:0.1rem;" });
  row.appendChild(badge);
  card.appendChild(row);

  card.appendChild(el("div", { className: "card-title", textContent: item.title }));
  card.appendChild(el("div", { className: "card-desc",  textContent: item.desc  }));

  // Links
  if (item.links && item.links.length) {
    var linksDiv = el("div", { className: "card-links" });
    item.links.forEach(function(lnk) {
      var a = el("a", { className: "card-link", href: lnk.href,
        target: "_blank", rel: "noopener noreferrer", textContent: lnk.label });
      linksDiv.appendChild(a);
    });
    card.appendChild(linksDiv);
  }

  // Primary action button
  var btnEl = el("a", {
    className: "btn btn-card-muted btn-sm",
    href: "#",
    textContent: "Not generated \u2014 see summary",
    "aria-disabled": "true",
    tabindex: "-1",
    style: "margin-top:0.8rem;align-self:flex-start;",
  });
  card.appendChild(btnEl);

  return card;
}

function renderCardGrid(containerId, dataArray) {
  var container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";
  dataArray.forEach(function(item) {
    container.appendChild(_buildCard(item));
  });
}

/* Validation section removed from UI (Stage UI-4 redesign) */

/* ----------------------------------------------------------------
   Render: Gallery (grouped)
   Items store data attributes so _applyGalleryImages can find them.
---------------------------------------------------------------- */
function renderGallery(containerId) {
  var container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";

  DASHBOARD_DATA.galleryGroups.forEach(function(group) {
    var groupDiv = el("div", { className: "gallery-group" });
    groupDiv.appendChild(el("div", { className: "gallery-section-title", textContent: group.label }));

    var grid = el("div", { className: "gallery-grid" });
    group.items.forEach(function(item) {
      var wrapper = el("div", { className: "gallery-item",
        tabindex: "0", role: "button", "aria-label": "View " + item.title,
        "data-gallery-item": "1",
        "data-img-src":      item.src        || "",
        "data-img-src2":     item.srcFallback || "",
        "data-img-href":     item.href        || item.src || "",
        "data-html-href":    item.htmlFallback || item.href || "",
        "data-img-title":    item.title,
        "data-extra-href":   item.extraHref  || "",
        "data-extra-label":  item.extraLabel || "",
      });

      // Placeholder (replaced later by _applyGalleryImages)
      var ph = el("div", { className: "gallery-thumb-placeholder" });
      ph.appendChild(el("div", { className: "placeholder-icon", innerHTML: "&#128444;" }));
      ph.appendChild(el("div", { textContent: "Checking\u2026" }));
      wrapper.appendChild(ph);

      wrapper.appendChild(el("div", { className: "gallery-caption", textContent: item.title }));
      if (item.sub) wrapper.appendChild(el("div", { className: "gallery-caption-sub", textContent: item.sub }));

      grid.appendChild(wrapper);
    });

    groupDiv.appendChild(grid);
    container.appendChild(groupDiv);
  });
}

/* ----------------------------------------------------------------
   Footer year + manifest date
---------------------------------------------------------------- */
function setFooterYear() {
  var el2 = document.getElementById("footer-year");
  if (el2) el2.textContent = DASHBOARD_DATA.year;
}

/* ----------------------------------------------------------------
   initSmoothScroll
---------------------------------------------------------------- */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener("click", function(e) {
      var hash = this.getAttribute("href");
      if (!hash || hash === "#") return;
      var target = document.querySelector(hash);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      if (history && history.pushState) history.pushState(null, "", hash);
    });
  });
}

/* ================================================================
   Manifest Integration — reads window.DASHBOARD_MANIFEST
================================================================ */

function applyManifest(manifest) {
  if (!manifest || manifest.isStub || !manifest.artifacts) return;

  var available = {};
  Object.values(manifest.artifacts).forEach(function(catList) {
    catList.forEach(function(art) {
      if (art.exists) available[art.relativePath] = art;
    });
  });

  _applyCardBadges(manifest, available);
  _applyGalleryImages(available);
  _applyHeroStats(manifest);
  _applyHeroPreview(available);
  _applyTechnicalDetails(manifest);
  _applyFooterNote(manifest);
}

/* ---- Update card badges + buttons ---- */
function _applyCardBadges(manifest, available) {
  var allCards = DASHBOARD_DATA.mainResults
    .concat(DASHBOARD_DATA.diagnostics)
    .concat(DASHBOARD_DATA.exportDocs);

  allCards.forEach(function(item) {
    var cardEl = document.getElementById(item.id);
    if (!cardEl) return;
    var mapping = CARD_MANIFEST_MAP[item.id];
    if (!mapping) return;

    // Gather all artifacts for this card
    var allArts = [];
    mapping.categories.forEach(function(cat) {
      var catList = manifest.artifacts[cat] || [];
      allArts = allArts.concat(catList);
    });
    var seen = new Set();
    var unique = allArts.filter(function(a) {
      if (seen.has(a.relativePath)) return false;
      seen.add(a.relativePath);
      return true;
    });
    var availArts = unique.filter(function(a) { return a.exists; });
    var hasAny = availArts.length > 0;

    // Resolve primary href
    var primaryHref = null;
    if (item.id === "paraview") {
      var vtkList = manifest.artifacts.vtk || [];
      var first = vtkList.find(function(a) { return a.exists; });
      if (first) primaryHref = first.relativePath;
    } else {
      (mapping.primaryPriority || []).some(function(p) {
        if (available[p]) { primaryHref = p; return true; }
        return false;
      });
    }

    // Badge
    var badge = cardEl.querySelector(".badge");
    if (badge) {
      if (hasAny) {
        var partial = availArts.length < unique.length;
        badge.className = partial ? "badge badge-partial" : "badge badge-available";
        badge.textContent = partial ? "PARTIAL" : "AVAILABLE";
      } else if (item.id === "paraview") {
        badge.className = "badge badge-planned";
        badge.textContent = "PLANNED";
      } else {
        badge.className = "badge badge-not-available";
        badge.textContent = "N/A";
      }
    }

    // Button
    var btn = cardEl.querySelector(".btn");
    if (btn) {
      if (primaryHref) {
        btn.className = "btn btn-card btn-sm";
        btn.setAttribute("href", primaryHref);
        btn.setAttribute("target", "_blank");
        btn.setAttribute("rel", "noopener noreferrer");
        btn.removeAttribute("aria-disabled");
        btn.removeAttribute("tabindex");
        btn.textContent = (mapping.openLabel || "Open") + " \u2192";
      } else if (item.id === "paraview") {
        btn.className = "btn btn-card-muted btn-sm";
        btn.textContent = "Planned for Stage UI\u20114";
        btn.setAttribute("aria-disabled", "true");
        btn.setAttribute("href", "#export");
      } else {
        btn.className = "btn btn-card-muted btn-sm";
        btn.textContent = "Not generated \u2014 see summary";
        btn.setAttribute("aria-disabled", "true");
        btn.setAttribute("href", "#export");
      }
    }

    // Link visibility: show only existing links
    var linksDiv = cardEl.querySelector(".card-links");
    if (linksDiv) {
      linksDiv.querySelectorAll(".card-link").forEach(function(a) {
        var href = a.getAttribute("href");
        if (href && !available[href]) {
          a.style.display = "none";
        }
      });
    }
  });
}

/* ---- Gallery: resolve each item to image / HTML-card / placeholder ---- */
function _applyGalleryImages(available) {
  document.querySelectorAll("[data-gallery-item='1']").forEach(function(wrapper) {
    var src        = wrapper.getAttribute("data-img-src")    || "";
    var src2       = wrapper.getAttribute("data-img-src2")   || "";
    var href       = wrapper.getAttribute("data-img-href")   || "";
    var htmlHref   = wrapper.getAttribute("data-html-href")  || "";
    var title      = wrapper.getAttribute("data-img-title")  || "";
    var extraHref  = wrapper.getAttribute("data-extra-href") || "";
    var extraLabel = wrapper.getAttribute("data-extra-label")|| "";

    // Determine which image source to use (primary → fallback)
    var imgSrc = null;
    if (src  && available[src])  imgSrc = src;
    if (!imgSrc && src2 && available[src2]) imgSrc = src2;

    var ph = wrapper.querySelector(".gallery-thumb-placeholder");

    if (imgSrc) {
      // --- Case 1: image exists → show <img> with lightbox ---
      var img = document.createElement("img");
      img.src = imgSrc;
      img.alt = title;
      img.className = "gallery-thumb";
      img.loading = "lazy";
      img.style.cursor = "pointer";

      if (ph) ph.parentNode.replaceChild(img, ph);

      // Lightbox opens the image; "Open original" goes to href
      var openHref = href || imgSrc;
      img.addEventListener("click", function(e) {
        e.stopPropagation();
        if (window._openLightbox) window._openLightbox(imgSrc, title, openHref);
      });
      // Re-wire wrapper key handler too
      wrapper.addEventListener("click", function(e) {
        if (e.target.tagName === "A") return;
        if (window._openLightbox) window._openLightbox(imgSrc, title, openHref);
      });
      wrapper.addEventListener("keydown", function(e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (window._openLightbox) window._openLightbox(imgSrc, title, openHref);
        }
      });

      // Extra action button (e.g. "Open interactive animation →")
      if (extraHref && extraLabel && available[extraHref]) {
        var extraBtn = document.createElement("a");
        extraBtn.className = "btn btn-card btn-sm gallery-extra-btn";
        extraBtn.href = extraHref;
        extraBtn.target = "_blank";
        extraBtn.rel = "noopener noreferrer";
        extraBtn.textContent = extraLabel;
        wrapper.appendChild(extraBtn);
      }

    } else if (htmlHref && available[htmlHref]) {
      // --- Case 2: no image but HTML exists → show interactive card ---
      var interactiveDiv = el("div", { className: "gallery-thumb-placeholder" });
      interactiveDiv.appendChild(el("div", { className: "placeholder-icon", innerHTML: "&#127760;" }));
      interactiveDiv.appendChild(el("div", {
        textContent: "Interactive viewer available",
        style: "font-weight:600;color:var(--primary);"
      }));
      var openBtn = el("a", {
        className: "btn btn-card btn-sm",
        href: htmlHref,
        target: "_blank",
        rel: "noopener noreferrer",
        textContent: "Open Interactive \u2192",
        style: "margin-top:0.5rem;",
      });
      interactiveDiv.appendChild(openBtn);

      if (ph) ph.parentNode.replaceChild(interactiveDiv, ph);

      // Clicking the card wrapper also opens HTML
      wrapper.style.cursor = "pointer";
      wrapper.addEventListener("click", function(e) {
        if (e.target.tagName === "A") return;
        window.open(htmlHref, "_blank", "noopener,noreferrer");
      });

    } else {
      // --- Case 3: nothing found → show specific "not generated" placeholder ---
      if (ph) {
        ph.innerHTML = "";
        ph.appendChild(el("div", { className: "placeholder-icon", innerHTML: "&#128444;" }));
        var reason = "Not generated";
        if (src && !available[src]) reason = "Image not yet generated";
        ph.appendChild(el("div", { textContent: reason, style: "font-size:0.76rem;color:var(--text-faint);" }));
        if (href) {
          ph.appendChild(el("a", {
            href: href, target: "_blank", rel: "noopener noreferrer",
            textContent: "Check HTML \u2192",
            className: "card-link",
            style: "margin-top:0.4rem;font-size:0.74rem;",
          }));
        }
      }
      wrapper.style.cursor = "default";
    }
  });
}

/* ---- Hero stats from manifest ---- */
function _applyHeroStats(manifest) {
  var summary = manifest.summaryData || {};

  function setText(id, val) {
    var el2 = document.getElementById(id);
    if (el2 && val !== undefined && val !== null) el2.textContent = val;
  }

  if (summary.latest_step_detected != null)
    setText("stat-steps", Number(summary.latest_step_detected).toLocaleString());
  else if (summary.latestStep != null)
    setText("stat-steps", Number(summary.latestStep).toLocaleString());

  if (summary.particle_total_count != null)
    setText("stat-particles", Number(summary.particle_total_count).toLocaleString());

  var available = manifest.availableCount;
  var missing   = manifest.missingCount;
  if (available !== undefined) {
    setText("stat-outputs", available.toLocaleString() + " available");
    var subEl = document.getElementById("stat-outputs-sub");
    if (subEl && missing !== undefined && missing > 0) {
      subEl.textContent = missing.toLocaleString() + " optional output" +
                          (missing === 1 ? "" : "s") + " not generated";
    } else if (subEl) {
      subEl.textContent = "All expected outputs generated";
    }
    var fill = document.getElementById("stat-outputs-fill");
    var bar  = document.getElementById("stat-outputs-bar");
    if (fill && bar && missing !== undefined) {
      var total = available + missing;
      var pct = total > 0 ? Math.round((available / total) * 100) : 100;
      fill.style.width = pct + "%";
      bar.setAttribute("aria-valuenow", String(pct));
      bar.setAttribute("aria-valuetext", available + " of " + total + " outputs available");
    }
  }
}

/* ---- Hero preview image (local files only) ---- */
function _applyHeroPreview(available) {
  var img      = document.getElementById("hero-preview-img");
  var fallback = document.getElementById("hero-preview-fallback");
  var link     = document.getElementById("hero-preview-link");
  if (!img && !fallback) return;

  var viewerHref = "html/particle_3d_temperature.html";
  var chosen = null;
  for (var i = 0; i < HERO_PREVIEW_CANDIDATES.length; i++) {
    if (available[HERO_PREVIEW_CANDIDATES[i]]) {
      chosen = HERO_PREVIEW_CANDIDATES[i];
      break;
    }
  }

  if (chosen && img) {
    img.src = chosen;
    img.hidden = false;
    if (fallback) fallback.style.display = "none";
  } else if (fallback) {
    fallback.style.display = "flex";
    if (img) img.hidden = true;
  }

  if (link && available[viewerHref]) {
    link.href = viewerHref;
  }
}

/* ---- Technical details (input folder — not in hero) ---- */
function _applyTechnicalDetails(manifest) {
  var summary = manifest.summaryData || {};
  var folder  = summary.input_folder;
  if (!folder) return;

  var display = folder.replace(/\\/g, "/");
  var parts   = display.split("/");
  if (parts.length > 4) display = "\u2026/" + parts.slice(-3).join("/");

  var footerEl = document.getElementById("footer-input-folder");
  if (footerEl)
    footerEl.textContent = "Input folder: " + display;

  var card = document.getElementById("tech-details");
  if (card) {
    var linksDiv = card.querySelector(".card-links");
    if (!linksDiv) {
      linksDiv = el("div", { className: "card-links" });
      card.appendChild(linksDiv);
    }
    if (!linksDiv.querySelector("[data-tech-folder]")) {
      var span = el("span", {
        className: "card-link",
        "data-tech-folder": "1",
        textContent: display,
        style: "cursor:default;opacity:0.85;",
      });
      linksDiv.appendChild(span);
    }
  }
}

/* ---- Footer note ---- */
function _applyFooterNote(manifest) {
  var dateEl = document.getElementById("footer-manifest-date");
  var noteEl = document.getElementById("footer-manifest-note");
  if (dateEl && manifest.generatedAt)
    dateEl.textContent = manifest.generatedAt.replace("T", " ").replace("Z", " UTC");
  if (noteEl)
    noteEl.textContent =
      manifest.availableCount + " artifacts available, " +
      manifest.missingCount + " pending. " +
      "Regenerate: python3 visualization/build_dashboard.py --input build/output --out visualization_output --verbose";
}

/* ================================================================
   DOMContentLoaded — wire everything up
================================================================ */
document.addEventListener("DOMContentLoaded", function() {
  initThemeToggle();
  initNavScrollSpy();
  initLightbox();
  renderTimeline("phase-timeline");
  renderCardGrid("main-results-cards",  DASHBOARD_DATA.mainResults);
  renderCardGrid("diagnostics-cards",   DASHBOARD_DATA.diagnostics);
  renderCardGrid("export-cards",        DASHBOARD_DATA.exportDocs);
  renderGallery("preview-gallery");
  initSmoothScroll();
  setFooterYear();

  var manifest = window.DASHBOARD_MANIFEST;
  if (manifest && !manifest.isStub) applyManifest(manifest);
});
