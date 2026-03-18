/* ================================================================
   CS-CME  –  Interactive Concept Map  –  D3.js Visualisation
   ================================================================ */

(() => {
  "use strict";

    // ====================== HERO HOMEPAGE TRANSITION ======================
    const hero = document.getElementById("hero");
    const appHeader = document.getElementById("app-header");
    const appContainer = document.getElementById("app-container");

    // Advanced hero launch with smooth transition
document.getElementById("btn-launch").addEventListener("click", () => {
  const hero = document.getElementById("hero");
  hero.style.transition = "opacity 0.8s ease, transform 0.8s ease";
  hero.style.opacity = "0";
  hero.style.transform = "scale(0.95)";

  setTimeout(() => {
    hero.style.display = "none";
    document.getElementById("app-header").style.display = "flex";
    document.getElementById("app-container").style.display = "flex";
  }, 800);
});

  const API_BASE = "";  // same-origin; change if backend is elsewhere

  // ── Cluster colour palette ──
  const CLUSTER_COLORS = [
    "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#06b6d4",
    "#84cc16", "#e11d48", "#0ea5e9", "#d946ef", "#10b981",
  ];

  // ── State ──
  let conceptMap = null;   // { nodes, edges }
  let simulation  = null;
  let svgGroup    = null;
  let zoom        = null;
  let physicsOn   = true;
  let currentHighlight = null;

  // ── DOM refs ──
  const $  = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const inputText    = $("#input-text");
  const inputFile    = $("#input-file");
  const fileName     = $("#file-name");
  const btnGenerate  = $("#btn-generate");
  const statusBar    = $("#status-bar");
  const warningsDiv  = $("#warnings");
  const statsDiv     = $("#stats");
  const controlsDiv  = $("#controls");
  const emptyState   = $("#empty-state");
  const graphSvg     = d3.select("#graph-svg");
  const tooltip      = $("#tooltip");
  const searchInput  = $("#search-input");
  const chkPhysics   = $("#chk-physics");
  const btnTheme     = $("#btn-theme");
  const detailPanel  = $("#detail-panel");
  // const minimapCanvas = $("#minimap-canvas");

  // ═══════════════════════════════════════════════════════════════
  //  THEME
  // ═══════════════════════════════════════════════════════════════
  btnTheme.addEventListener("click", () => {
    document.body.classList.toggle("dark-theme");
    document.body.classList.toggle("light-theme");
    // updateMinimap();
  });

  // ═══════════════════════════════════════════════════════════════
  //  TABS
  // ═══════════════════════════════════════════════════════════════
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => t.classList.remove("active"));
      $$(".tab-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      $(`#${tab.dataset.tab}`).classList.add("active");
    });
  });

  // ── File input label ──
  inputFile.addEventListener("change", () => {
    fileName.textContent = inputFile.files.length
      ? inputFile.files[0].name
      : "No file selected";
  });

  // ═══════════════════════════════════════════════════════════════
  //  GENERATE
  // ═══════════════════════════════════════════════════════════════
  btnGenerate.addEventListener("click", generate);

  async function generate() {
    btnGenerate.disabled = true;
    showStatus("Processing… this may take a moment.", "");
    warningsDiv.classList.add("hidden");
    statsDiv.classList.add("hidden");

    try {
      let resp;
      const activeTab = $(".tab.active").dataset.tab;

      if (activeTab === "file-tab" && inputFile.files.length) {
        const fd = new FormData();
        fd.append("file", inputFile.files[0]);
        resp = await fetch(`${API_BASE}/api/extract`, { method: "POST", body: fd });
      } else {
        const text = inputText.value.trim();
        if (!text) { showStatus("Please enter some text.", "error"); btnGenerate.disabled = false; return; }
        resp = await fetch(`${API_BASE}/api/extract`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
      }

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || `Server error ${resp.status}`);
      }

      const data = await resp.json();
      conceptMap = data.concept_map;

      // Warnings
      if (data.warnings && data.warnings.length) {
        warningsDiv.innerHTML = data.warnings.map((w) => `<p>&#9888; ${w}</p>`).join("");
        warningsDiv.classList.remove("hidden");
      }

      // Stats
      if (data.stats) {
        const s = data.stats;
        statsDiv.innerHTML = `
          <strong>Stats</strong><br>
          Sentences: ${s.total_sentences || 0}<br>
          Concepts extracted: ${s.total_concepts_extracted || 0}<br>
          Relations: ${s.total_relations_extracted || 0}<br>
          Nodes in map: ${s.concepts_in_map || 0}<br>
          Edges in map: ${s.edges_in_map || 0}<br>
          Clusters: ${s.communities_detected || 0}<br>
          Headings: ${s.headings_found || 0}`;
        statsDiv.classList.remove("hidden");
      }

      controlsDiv.classList.remove("hidden");
      emptyState.style.display = "none";
      showStatus("Concept map generated successfully!", "success");

      renderGraph(conceptMap);

    } catch (e) {
      showStatus(e.message, "error");
    } finally {
      btnGenerate.disabled = false;
    }
  }

  function showStatus(msg, type) {
    statusBar.textContent = msg;
    statusBar.className = type || "";
    statusBar.classList.remove("hidden");
  }

  // ═══════════════════════════════════════════════════════════════
  //  D3 FORCE GRAPH
  // ═══════════════════════════════════════════════════════════════
  function renderGraph(map) {
    graphSvg.selectAll("*").remove();

    if (!map || !map.nodes.length) { emptyState.style.display = "flex"; return; }

    const svgEl  = document.getElementById("graph-svg");
    const width  = svgEl.clientWidth;
    const height = svgEl.clientHeight;

    // ── Defs: arrow markers ──
    const defs = graphSvg.append("defs");
    defs.append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 22)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("class", "arrow-head");

    // ── Zoom ──
    zoom = d3.zoom()
      .scaleExtent([0.1, 6])
      .on("zoom", (event) => {
        svgGroup.attr("transform", event.transform);
        // updateMinimap();
      });
    graphSvg.call(zoom);

    svgGroup = graphSvg.append("g");

    // Prepare data  (D3 mutates arrays – work on copies)
    const nodes = map.nodes.map((n) => ({ ...n }));
    const edges = map.edges.map((e) => ({
      ...e,
      source: e.source,
      target: e.target,
    }));

    // Node size scale (by frequency)
    const maxFreq = d3.max(nodes, (d) => d.frequency) || 1;
    const rScale  = d3.scaleSqrt().domain([1, maxFreq]).range([8, 28]);

    // ── Links ──
    const linkGroup = svgGroup.append("g").attr("class", "links");
    const link = linkGroup.selectAll("line")
      .data(edges)
      .join("line")
      .attr("class", "link")
      .attr("marker-end", "url(#arrow)");

    // ── Link labels ──
    const linkLabelGroup = svgGroup.append("g").attr("class", "link-labels");
    const linkLabel = linkLabelGroup.selectAll("text")
      .data(edges)
      .join("text")
      .attr("class", "link-label")
      .text((d) => d.relation);

    // ── Nodes ──
    const nodeGroup = svgGroup.append("g").attr("class", "nodes");
    const node = nodeGroup.selectAll("g")
      .data(nodes, (d) => d.id)
      .join("g")
      .attr("class", "node-group")
      .call(d3.drag()
        .on("start", dragStarted)
        .on("drag", dragged)
        .on("end", dragEnded));

    node.append("circle")
      .attr("class", "node-circle")
      .attr("r", (d) => rScale(d.frequency || 1))
      .attr("fill", (d) => nodeColor(d));

    node.append("text")
      .attr("class", "node-label")
      .attr("dy", (d) => rScale(d.frequency || 1) + 12)
      .text((d) => d.id);

    // ── Tooltip ──
    node.on("mouseover", (event, d) => {
      tooltip.classList.remove("hidden");
      let html = `<strong>${d.id}</strong>`;
      if (d.frequency > 1) html += `<br>Frequency: ${d.frequency}`;
      if (d.cluster >= 0) html += `<br>Cluster: ${d.cluster}`;
      if (d.descriptions && d.descriptions.length) {
        html += `<br><em>${d.descriptions[0].substring(0, 120)}…</em>`;
      }
      tooltip.innerHTML = html;
    })
    .on("mousemove", (event) => {
      tooltip.style.left = (event.clientX + 14) + "px";
      tooltip.style.top  = (event.clientY + 14) + "px";
    })
    .on("mouseout", () => { tooltip.classList.add("hidden"); })
    .on("click", (event, d) => { showDetail(d, edges); });

    // ── Simulation ──
    simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id((d) => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d) => rScale(d.frequency || 1) + 10))
      .on("tick", ticked);

    function ticked() {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      linkLabel
        .attr("x", (d) => (d.source.x + d.target.x) / 2)
        .attr("y", (d) => (d.source.y + d.target.y) / 2);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);

      // updateMinimap();
    }

    // ── Drag callbacks ──
    function dragStarted(event, d) {
      if (!event.active && physicsOn) simulation.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    }
    function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
    function dragEnded(event, d) {
      if (!event.active && physicsOn) simulation.alphaTarget(0);
      if (physicsOn) { d.fx = null; d.fy = null; }
    }
  }

  // ── Node colour by cluster ──
  function nodeColor(d) {
    if (d.id === "Document_Root") return getComputedStyle(document.body).getPropertyValue("--node-root").trim();
    const idx = (d.cluster >= 0) ? d.cluster % CLUSTER_COLORS.length : 0;
    return CLUSTER_COLORS[idx];
  }

  // ═══════════════════════════════════════════════════════════════
  //  DETAIL PANEL
  // ═══════════════════════════════════════════════════════════════
  function showDetail(d, edges) {
    detailPanel.classList.remove("hidden");
    $("#detail-title").textContent = d.id;
    $("#detail-cluster").textContent = d.cluster >= 0 ? `Cluster ${d.cluster}` : "";
    $("#detail-cluster").style.background = nodeColor(d);
    $("#detail-cluster").style.color = "#fff";
    $("#detail-freq").textContent = `Frequency: ${d.frequency || 1}`;

    const descUl = $("#detail-descriptions");
    descUl.innerHTML = "";
    (d.descriptions || []).forEach((desc) => {
      const li = document.createElement("li");
      li.textContent = desc;
      descUl.appendChild(li);
    });
    if (!d.descriptions || !d.descriptions.length) {
      descUl.innerHTML = "<li style='color:var(--text-muted)'>No descriptions available.</li>";
    }

    const formUl = $("#detail-formulas");
    formUl.innerHTML = "";
    (d.formulas || []).forEach((f) => {
      const li = document.createElement("li");
      li.textContent = f;
      formUl.appendChild(li);
    });
    if (!d.formulas || !d.formulas.length) {
      formUl.innerHTML = "<li style='color:var(--text-muted)'>No formulas detected.</li>";
    }

    const relUl = $("#detail-relations");
    relUl.innerHTML = "";
    const allEdges = edges || (conceptMap ? conceptMap.edges : []);
    allEdges.forEach((e) => {
      const src = typeof e.source === "object" ? e.source.id : e.source;
      const tgt = typeof e.target === "object" ? e.target.id : e.target;
      if (src === d.id || tgt === d.id) {
        const li = document.createElement("li");
        li.textContent = `${src} → ${e.relation} → ${tgt}`;
        if (e.negated) li.textContent += " [NEGATED]";
        relUl.appendChild(li);
      }
    });
    if (!relUl.children.length) {
      relUl.innerHTML = "<li style='color:var(--text-muted)'>No direct relations.</li>";
    }
  }

  $("#btn-close-detail").addEventListener("click", () => {
    detailPanel.classList.add("hidden");
  });

  // ═══════════════════════════════════════════════════════════════
  //  SEARCH
  // ═══════════════════════════════════════════════════════════════
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.trim().toLowerCase();
    d3.selectAll(".node-group").classed("node-highlight", false);

    if (!q) { currentHighlight = null; return; }

    d3.selectAll(".node-group").each(function (d) {
      if (d.id.toLowerCase().includes(q)) {
        d3.select(this).classed("node-highlight", true);
        currentHighlight = d;
      }
    });

    // Pan to first match
    if (currentHighlight && zoom && svgGroup) {
      const svgEl = document.getElementById("graph-svg");
      const w = svgEl.clientWidth, h = svgEl.clientHeight;
      const t = d3.zoomIdentity.translate(w / 2 - currentHighlight.x, h / 2 - currentHighlight.y);
      graphSvg.transition().duration(500).call(zoom.transform, t);
    }
  });

  // ═══════════════════════════════════════════════════════════════
  //  PHYSICS TOGGLE
  // ═══════════════════════════════════════════════════════════════
  chkPhysics.addEventListener("change", () => {
    physicsOn = chkPhysics.checked;
    if (simulation) {
      if (physicsOn) {
        simulation.alpha(0.3).restart();
      } else {
        simulation.stop();
      }
    }
  });

  // ═══════════════════════════════════════════════════════════════
  //  EXPORT JSON
  // ═══════════════════════════════════════════════════════════════
  $("#btn-export-json").addEventListener("click", () => {
    if (!conceptMap) return;
    // Clean for export: strip D3 internal fields
    const clean = {
      nodes: conceptMap.nodes.map((n) => ({
        id: n.id, frequency: n.frequency,
        descriptions: n.descriptions || [], formulas: n.formulas || [],
        cluster: n.cluster,
      })),
      edges: conceptMap.edges.map((e) => ({
        source: typeof e.source === "object" ? e.source.id : e.source,
        target: typeof e.target === "object" ? e.target.id : e.target,
        relation: e.relation, negated: e.negated,
      })),
    };
    const blob = new Blob([JSON.stringify(clean, null, 2)], { type: "application/json" });
    downloadBlob(blob, "concept_map.json");
  });

  // ═══════════════════════════════════════════════════════════════
  //  EXPORT PNG
  // ═══════════════════════════════════════════════════════════════
  $("#btn-export-png").addEventListener("click", () => {
    const svgEl = document.getElementById("graph-svg");
    const serializer = new XMLSerializer();
    const svgString  = serializer.serializeToString(svgEl);

    const canvas = document.createElement("canvas");
    canvas.width  = svgEl.clientWidth  * 2;
    canvas.height = svgEl.clientHeight * 2;
    const ctx = canvas.getContext("2d");
    ctx.scale(2, 2);

    const img = new Image();
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);
    img.onload = () => {
      // Fill background
      const bg = getComputedStyle(document.body).getPropertyValue("--bg").trim();
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => downloadBlob(blob, "concept_map.png"), "image/png");
    };
    img.src = url;
  });

  function downloadBlob(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ═══════════════════════════════════════════════════════════════
  //  MINI-MAP
  // ═══════════════════════════════════════════════════════════════
//   function updateMinimap() {
//     if (!conceptMap || !conceptMap.nodes.length) return;

//     const ctx = minimapCanvas.getContext("2d");
//     const mw = minimapCanvas.width;
//     const mh = minimapCanvas.height;

//     const bg = getComputedStyle(document.body).getPropertyValue("--panel-bg").trim();
//     ctx.fillStyle = bg;
//     ctx.fillRect(0, 0, mw, mh);

//     // Compute bounding box of all nodes
//     let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
//     conceptMap.nodes.forEach((n) => {
//       const nx = n.x != null ? n.x : 0;
//       const ny = n.y != null ? n.y : 0;
//       if (nx < minX) minX = nx;
//       if (ny < minY) minY = ny;
//       if (nx > maxX) maxX = nx;
//       if (ny > maxY) maxY = ny;
//     });

//     const pad = 40;
//     const rangeX = (maxX - minX) || 1;
//     const rangeY = (maxY - minY) || 1;
//     const scale  = Math.min((mw - pad) / rangeX, (mh - pad) / rangeY);
//     const offX   = (mw - rangeX * scale) / 2;
//     const offY   = (mh - rangeY * scale) / 2;

//     // Draw edges
//     ctx.strokeStyle = getComputedStyle(document.body).getPropertyValue("--edge-color").trim();
//     ctx.lineWidth = 0.5;
//     conceptMap.edges.forEach((e) => {
//       const s = typeof e.source === "object" ? e.source : conceptMap.nodes.find((n) => n.id === e.source);
//       const t = typeof e.target === "object" ? e.target : conceptMap.nodes.find((n) => n.id === e.target);
//       if (!s || !t) return;
//       const sx = (((s.x || 0) - minX) * scale) + offX;
//       const sy = (((s.y || 0) - minY) * scale) + offY;
//       const tx = (((t.x || 0) - minX) * scale) + offX;
//       const ty = (((t.y || 0) - minY) * scale) + offY;
//       ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(tx, ty); ctx.stroke();
//     });

//     // Draw nodes
//     conceptMap.nodes.forEach((n) => {
//       const nx = (((n.x || 0) - minX) * scale) + offX;
//       const ny = (((n.y || 0) - minY) * scale) + offY;
//       ctx.fillStyle = nodeColor(n);
//       ctx.beginPath(); ctx.arc(nx, ny, 2.5, 0, Math.PI * 2); ctx.fill();
//     });

//     // Viewport indicator
//     const svgEl = document.getElementById("graph-svg");
//     const transform = d3.zoomTransform(svgEl);
//     const vpLeft   = (-transform.x / transform.k - minX) * scale + offX;
//     const vpTop    = (-transform.y / transform.k - minY) * scale + offY;
//     const vpWidth  = (svgEl.clientWidth  / transform.k) * scale;
//     const vpHeight = (svgEl.clientHeight / transform.k) * scale;

//     const vp = $("#minimap-viewport");
//     vp.style.left   = Math.max(0, vpLeft) + "px";
//     vp.style.top    = Math.max(0, vpTop) + "px";
//     vp.style.width  = Math.min(mw, vpWidth) + "px";
//     vp.style.height = Math.min(mh, vpHeight) + "px";
//   }

 })();
