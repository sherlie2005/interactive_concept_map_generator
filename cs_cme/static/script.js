const dom = {
  inputText: document.getElementById("inputText"),
  pdfFile: document.getElementById("pdfFile"),
  pdfFileName: document.getElementById("pdfFileName"),
  generateBtn: document.getElementById("generateBtn"),
  clearBtn: document.getElementById("clearBtn"),
  loadingSpinner: document.getElementById("loadingSpinner"),
  statusText: document.getElementById("statusText"),
  nodeCount: document.getElementById("nodeCount"),
  edgeCount: document.getElementById("edgeCount"),
  svg: document.getElementById("graphSvg"),
  graphArea: document.getElementById("graphArea"),
  miniMap: document.getElementById("miniMap"),
  nodeTooltip: document.getElementById("nodeTooltip"),
  emptyState: document.getElementById("emptyState"),
  searchInput: document.getElementById("searchInput"),
  searchClearBtn: document.getElementById("searchClearBtn"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  resetLayoutBtn: document.getElementById("resetLayoutBtn"),
  togglePhysicsBtn: document.getElementById("togglePhysicsBtn"),
  exportPngBtn: document.getElementById("exportPngBtn"),
  exportJsonBtn: document.getElementById("exportJsonBtn"),
  detailsPanel: document.getElementById("detailsPanel"),
  detailsBody: document.getElementById("detailsBody"),
  closeDetailsBtn: document.getElementById("closeDetailsBtn")
};

const state = {
  raw: { nodes: [], edges: [] },
  nodes: [],
  edges: [],
  nodeById: new Map(),
  adjacency: new Map(),
  linksByNode: new Map(),
  physicsEnabled: true,
  selectedNode: null,
  searchTerm: "",
  hoveredNodeId: null,
  theme: "dark"
};

const svg = d3.select(dom.svg);
const rootLayer = svg.append("g").attr("class", "root-layer");
const edgeLayer = rootLayer.append("g").attr("class", "edge-layer");
const labelLayer = rootLayer.append("g").attr("class", "label-layer");
const nodeLayer = rootLayer.append("g").attr("class", "node-layer");

const markerDefs = svg.append("defs");
const arrowMarker = markerDefs.append("marker").attr("id", "arrow");
const negArrowMarker = markerDefs.append("marker").attr("id", "arrow-negated");

configureMarker(arrowMarker, "rgba(140,163,204,0.85)");
configureMarker(negArrowMarker, "rgba(239,71,111,0.95)");

const zoom = d3
  .zoom()
  .scaleExtent([0.2, 3.2])
  .on("zoom", (event) => {
    rootLayer.attr("transform", event.transform.toString());
    renderMiniMap(event.transform);
  });

svg.call(zoom);

let edgeSelection = edgeLayer.selectAll("path.edge");
let edgeLabelSelection = labelLayer.selectAll("text.edge-label");
let nodeSelection = nodeLayer.selectAll("g.node");

let simulation = d3
  .forceSimulation([])
  .force("link", d3.forceLink([]).id((d) => d.id).distance(linkDistance).strength(0.24))
  .force("charge", d3.forceManyBody().strength(-700))
  .force("center", d3.forceCenter(dom.graphArea.clientWidth/2, dom.graphArea.clientHeight/2))
  .force("collision", d3.forceCollide().radius((d) => d.radius + 12))
  .alphaDecay(0.04)
  .on("tick", onTick);

initTheme();
bindEvents();
setStatus("Idle");

function bindEvents() {
  dom.generateBtn.addEventListener("click", handleGenerate);
  dom.pdfFile.addEventListener("change", handlePdfSelection);
  dom.clearBtn.addEventListener("click", clearGraph);
  dom.searchInput.addEventListener("input", handleSearch);
  dom.searchClearBtn.addEventListener("click", clearSearch);
  dom.themeToggleBtn.addEventListener("click", toggleTheme);
  dom.resetLayoutBtn.addEventListener("click", resetLayout);
  dom.togglePhysicsBtn.addEventListener("click", togglePhysics);
  dom.exportJsonBtn.addEventListener("click", exportJson);
  dom.exportPngBtn.addEventListener("click", exportPng);
  dom.closeDetailsBtn.addEventListener("click", closeDetails);
  dom.miniMap.addEventListener("click", handleMiniMapClick);
  window.addEventListener("resize", handleResize);
  handleResize();
}

async function handleGenerate() {
  const text = dom.inputText.value.trim();
  const pdf = dom.pdfFile.files[0];

  if (!text && !pdf) {
    setStatus("Enter text or upload a PDF to generate a graph");
    return;
  }

  setLoading(true);
  setStatus("Generating concept map...");

  try {
    let response;

    if (pdf) {
      const formData = new FormData();
      formData.append("pdf", pdf);
      formData.append("text", text);

      response = await fetch("/generate", {
        method: "POST",
        body: formData
      });
    } else {
      response = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
    }

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `Request failed (${response.status})`);
    }

    hydrateGraph(payload);
    setStatus(pdf ? "Graph generated from PDF/text" : "Graph generated");
  } catch (error) {
    console.error(error);
    const message = error.message || "unable to generate graph";
    setStatus(`Error: ${message}`);
    window.alert(`Generation failed: ${message}`);
  } finally {
    setLoading(false);
  }
}

function handlePdfSelection() {
  const file = dom.pdfFile.files[0];
  dom.pdfFileName.textContent = file ? `Selected: ${file.name}` : "No PDF selected";
}

function hydrateGraph(payload) {
  const nodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
const edges = Array.isArray(payload?.edges) ? payload.edges : [];

// keep only most important nodes for visualization
const TOP_NODES = 60;

const sortedNodes = [...nodes].sort((a, b) => (b.frequency || 1) - (a.frequency || 1));
const selectedIds = new Set(sortedNodes.slice(0, TOP_NODES).map(n => n.id));

const filteredEdges = edges.filter(e => selectedIds.has(e.source) && selectedIds.has(e.target));
const filteredNodes = sortedNodes.slice(0, TOP_NODES);

  state.raw = { nodes: structuredClone(filteredNodes), edges: structuredClone(filteredEdges) };
  state.nodes = filteredNodes.map((node, idx) => ({
    ...node,
    frequency: Number(node.frequency) || 1,
    descriptions: Array.isArray(node.descriptions) ? node.descriptions : [],
    x: idx * 20 + (Math.random() - 0.5) * 120,
    y: idx * 15 + (Math.random() - 0.5) * 120
  }));

  // assign cluster groups
  state.nodes.forEach(n => {

    const name = n.id.toLowerCase()

    if (name.includes("model"))
        n.group = "modeling"

    else if (name.includes("cassandra"))
        n.group = "cassandra"

    else if (name.includes("application"))
        n.group = "applications"

    else
        n.group = "general"
  })

  const freqExtent = d3.extent(state.nodes, (n) => n.frequency);
  const radiusScale = d3
    .scaleLinear()
    .domain(freqExtent[0] === freqExtent[1] ? [freqExtent[0] || 0, (freqExtent[1] || 0) + 1] : freqExtent)
    .range([16, 42]);

  const colorScale = d3
    .scaleLinear()
    .domain([0, 0.5, 1])
    .range(["#4cc9f0", "#7b61ff", "#ff4fd8"])
    .interpolate(d3.interpolateRgb);

  const maxFrequency = d3.max(state.nodes, (n) => n.frequency) || 1;
  state.nodes.forEach((n) => {

    n.radius = radiusScale(n.frequency);
    n.fill = colorScale(n.frequency / maxFrequency);

    // make document root large and gold
    if (n.id === "document_root") {
        n.radius = 40;
        n.fill = "#FFD84D";
    }

});

  state.nodeById = new Map(state.nodes.map((n) => [n.id, n]));
  state.edges = filteredEdges
    .filter((e) => state.nodeById.has(e.source) && state.nodeById.has(e.target))
    .map((e) => ({
      ...e,
      weight: Math.max(1, Number(e.weight) || 1),
      negated: Boolean(e.negated)
    }));

  buildAdjacency();
  drawGraph();
  closeDetails();
  clearSearch();

  dom.emptyState.style.display = state.nodes.length ? "none" : "grid";
  updateCounters();

  simulation.nodes(state.nodes);
  simulation.force("link").links(state.edges);
  simulation.alpha(1).restart();

  const identity = d3.zoomIdentity.translate(dom.graphArea.clientWidth / 2, dom.graphArea.clientHeight / 2).scale(0.9);
  svg.transition().duration(500).call(zoom.transform, identity);
}

function buildAdjacency() {
  state.adjacency = new Map();
  state.linksByNode = new Map();

  state.nodes.forEach((n) => {
    state.adjacency.set(n.id, new Set([n.id]));
    state.linksByNode.set(n.id, []);
  });

  state.edges.forEach((e) => {
    state.adjacency.get(e.source)?.add(e.target);
    state.adjacency.get(e.target)?.add(e.source);
    state.linksByNode.get(e.source)?.push(e);
    state.linksByNode.get(e.target)?.push(e);
  });
}

function drawGraph() {
  edgeSelection = edgeLayer
    .selectAll("path.edge")
    .data(state.edges, (d) => `${d.source}->${d.target}:${d.relation}`)
    .join("path")
    .attr("class", (d) => (d.negated ? "edge negated" : "edge"))
    .attr("marker-end", (d) => `url(#${d.negated ? "arrow-negated" : "arrow"})`)
    .attr("stroke-width", (d) => 1 + Math.min(4, d.weight * 0.75));

  edgeLabelSelection = labelLayer
    .selectAll("text.edge-label")
    .data(state.edges, (d) => `${d.source}->${d.target}:${d.relation}`)
    .join("text")
    .attr("class", "edge-label")
    .text((d) => d.relation || "related_to");

  const dragBehavior = d3
    .drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.18).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      if (!state.physicsEnabled) return;
      d.fx = null;
      d.fy = null;
    });

  nodeSelection = nodeLayer
    .selectAll("g.node")
    .data(state.nodes, (d) => d.id)
    .join((enter) => {
      const g = enter.append("g").attr("class", "node");

      g.append("circle")
        .attr("stroke-width", 2)
        .attr("r", (d) => d.radius)
        .attr("fill", (d) => d.fill)
        .attr("opacity", 0.94);

      g.append("text")
        .attr("class", "node-label")
        .attr("dy", 4)
        .text((d) => truncateLabel(d.id));

      return g;
    });

  nodeSelection
    .on("mouseenter", (event, d) => {
      state.hoveredNodeId = d.id;
      applyHighlights();
      showNodeTooltip(event, d);
    })
    .on("mousemove", (event, d) => {
      showNodeTooltip(event, d);
    })
    .on("mouseleave", () => {
      state.hoveredNodeId = null;
      applyHighlights();
      hideNodeTooltip();
    })
    .on("click", (_, d) => openDetails(d))
    .call(dragBehavior);
}

function onTick() {
  edgeSelection.attr("d", (d) => straightPath(d));
  edgeLabelSelection.attr("x", (d) => edgeLabelPoint(d).x).attr("y", (d) => edgeLabelPoint(d).y);
  nodeSelection.attr("transform", (d) => `translate(${d.x},${d.y})`);
  renderMiniMap(d3.zoomTransform(dom.svg));
}

function straightPath(edge) {
  const source = resolveNode(edge.source);
  const target = resolveNode(edge.target);
  if (!source || !target) return "";
  return `M${source.x},${source.y} L${target.x},${target.y}`;
}

function edgeLabelPoint(edge) {
  const source = resolveNode(edge.source);
  const target = resolveNode(edge.target);
  if (!source || !target) return { x: 0, y: 0 };

  return {
    x: (source.x + target.x) / 2,
    y: (source.y + target.y) / 2 - 8
  };
}

function resolveNode(nodeRef) {
  if (!nodeRef) return null;
  if (typeof nodeRef === "object" && nodeRef.id) return nodeRef;
  return state.nodeById.get(nodeRef) || null;
}

function handleSearch() {
  state.searchTerm = dom.searchInput.value.trim().toLowerCase();
  applyHighlights();

  if (!state.searchTerm) return;

  const match = state.nodes.find((n) => n.id.toLowerCase().includes(state.searchTerm));
  if (match) {
    centerOnNode(match);
  }
}

function clearSearch() {
  dom.searchInput.value = "";
  state.searchTerm = "";
  applyHighlights();
}

function applyHighlights() {
  const activeSet = new Set();

  if (state.hoveredNodeId) {
    state.adjacency.get(state.hoveredNodeId)?.forEach((id) => activeSet.add(id));
  }

  if (state.searchTerm) {
    state.nodes
      .filter((n) => n.id.toLowerCase().includes(state.searchTerm))
      .forEach((n) => activeSet.add(n.id));
  }

  if (!activeSet.size) {
    nodeSelection.classed("dimmed", false).classed("highlight", false);
    edgeSelection.classed("dimmed", false).classed("highlight", false);
    edgeLabelSelection.classed("dimmed", false).classed("highlight", false);
    return;
  }

  nodeSelection.classed("highlight", (d) => activeSet.has(d.id)).classed("dimmed", (d) => !activeSet.has(d.id));

  edgeSelection
    .classed("highlight", (d) => activeSet.has(d.source.id || d.source) && activeSet.has(d.target.id || d.target))
    .classed("dimmed", (d) => !(activeSet.has(d.source.id || d.source) && activeSet.has(d.target.id || d.target)));

  edgeLabelSelection
    .classed("highlight", (d) => activeSet.has(d.source.id || d.source) && activeSet.has(d.target.id || d.target))
    .classed("dimmed", (d) => !(activeSet.has(d.source.id || d.source) && activeSet.has(d.target.id || d.target)));
}

function openDetails(node) {
  state.selectedNode = node;
  const connected = state.linksByNode.get(node.id) || [];

  const relations = connected.map((edge) => {
    const other = edge.source === node.id || edge.source?.id === node.id ? edge.target : edge.source;
    const otherId = typeof other === "object" ? other.id : other;
    return `${otherId} (${edge.relation || "related_to"})`;
  });

  const descriptions = node.descriptions.length ? node.descriptions : ["No descriptions available."];

  dom.detailsBody.innerHTML = `
    <h3>${escapeHtml(node.id)}</h3>
    <p><strong>Frequency:</strong> ${node.frequency}</p>
    <p><strong>Descriptions</strong></p>
    <ul>${descriptions.map((d) => `<li>${escapeHtml(d)}</li>`).join("")}</ul>
    <p><strong>Connected Concepts</strong></p>
    <ul>${(relations.length ? relations : ["No connected concepts"]).map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
  `;

  dom.detailsPanel.classList.add("open");
}

function closeDetails() {
  state.selectedNode = null;
  dom.detailsPanel.classList.remove("open");
  dom.detailsBody.innerHTML = "<p>Select a node to inspect details.</p>";
}

function clearGraph() {
  state.raw = { nodes: [], edges: [] };
  state.nodes = [];
  state.edges = [];
  state.nodeById = new Map();
  state.adjacency = new Map();
  state.linksByNode = new Map();
  state.hoveredNodeId = null;
  state.searchTerm = "";
  if (dom.pdfFile) dom.pdfFile.value = "";
  if (dom.pdfFileName) dom.pdfFileName.textContent = "No PDF selected";

  hideNodeTooltip();
  edgeSelection = edgeLayer.selectAll("path.edge").data([]).join("path");
  edgeLabelSelection = labelLayer.selectAll("text.edge-label").data([]).join("text");
  nodeSelection = nodeLayer.selectAll("g.node").data([]).join("g");

  simulation.nodes([]);
  simulation.force("link").links([]);
  simulation.stop();

  dom.emptyState.style.display = "grid";
  closeDetails();
  clearSearch();
  updateCounters();
  setStatus("Graph cleared");
  renderMiniMap(d3.zoomTransform(dom.svg));
}

function resetLayout() {
  if (!state.nodes.length) return;
  state.nodes.forEach((n, idx) => {
    n.x = (Math.random() - 0.5) * 220 + idx * 2;
    n.y = (Math.random() - 0.5) * 220 + idx * 2;
    n.fx = null;
    n.fy = null;
  });
  simulation.alpha(1).restart();
  setStatus("Layout reset");
}

function togglePhysics() {
  state.physicsEnabled = !state.physicsEnabled;

  if (state.physicsEnabled) {
    state.nodes.forEach((n) => {
      n.fx = null;
      n.fy = null;
    });
    simulation.alpha(0.7).restart();
    dom.togglePhysicsBtn.textContent = "Pause Physics";
    setStatus("Physics enabled");
  } else {
    state.nodes.forEach((n) => {
      n.fx = n.x;
      n.fy = n.y;
    });
    simulation.stop();
    dom.togglePhysicsBtn.textContent = "Resume Physics";
    setStatus("Physics paused");
  }
}

function exportJson() {
  if (!state.raw.nodes.length) return;
  const blob = new Blob([JSON.stringify(state.raw, null, 2)], { type: "application/json" });
  downloadBlob(blob, `concept-map-${Date.now()}.json`);
}

function exportPng() {
  if (!state.nodes.length) return;

  const serializer = new XMLSerializer();
  const source = serializer.serializeToString(dom.svg);
  const svgBlob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);
  const image = new Image();

  image.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = dom.graphArea.clientWidth * 2;
    canvas.height = dom.graphArea.clientHeight * 2;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(2, 0, 0, 2, 0, 0);
    const bodyBg = getComputedStyle(document.body).getPropertyValue("--bg-main");
    ctx.fillStyle = bodyBg.includes("gradient") ? "#0b1023" : bodyBg.trim() || "#0b1023";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, dom.graphArea.clientWidth, dom.graphArea.clientHeight);

    canvas.toBlob((blob) => {
      if (blob) downloadBlob(blob, `concept-map-${Date.now()}.png`);
    }, "image/png");

    URL.revokeObjectURL(url);
  };

  image.src = url;
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function renderMiniMap(transform) {
  const canvas = dom.miniMap;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--mini-bg").trim() || "rgba(4,8,20,0.75)";
  ctx.fillRect(0, 0, width, height);

  if (!state.nodes.length) return;

  const bounds = graphBounds();
  const mapPadding = 12;
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const scale = Math.min((width - mapPadding * 2) / spanX, (height - mapPadding * 2) / spanY);

  const toMap = (x, y) => ({
    x: (x - bounds.minX) * scale + mapPadding,
    y: (y - bounds.minY) * scale + mapPadding
  });

  ctx.strokeStyle = "rgba(129,151,201,0.4)";
  ctx.lineWidth = 1;
  state.edges.forEach((e) => {
    const s = resolveNode(e.source);
    const t = resolveNode(e.target);
    if (!s || !t) return;
    const p1 = toMap(s.x, s.y);
    const p2 = toMap(t.x, t.y);
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  });

  state.nodes.forEach((n) => {
    const p = toMap(n.x, n.y);
    ctx.beginPath();
    ctx.fillStyle = n.fill;
    ctx.arc(p.x, p.y, Math.max(2, n.radius * 0.11), 0, Math.PI * 2);
    ctx.fill();
  });

  const viewW = dom.graphArea.clientWidth / transform.k;
  const viewH = dom.graphArea.clientHeight / transform.k;
  const viewX = -transform.x / transform.k;
  const viewY = -transform.y / transform.k;

  const topLeft = toMap(viewX, viewY);
  const bottomRight = toMap(viewX + viewW, viewY + viewH);

  ctx.strokeStyle = "rgba(76,201,240,0.9)";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(topLeft.x, topLeft.y, bottomRight.x - topLeft.x, bottomRight.y - topLeft.y);
}

function handleMiniMapClick(event) {
  if (!state.nodes.length) return;

  const rect = dom.miniMap.getBoundingClientRect();
  const clickX = ((event.clientX - rect.left) / rect.width) * dom.miniMap.width;
  const clickY = ((event.clientY - rect.top) / rect.height) * dom.miniMap.height;

  const bounds = graphBounds();
  const mapPadding = 12;
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const scale = Math.min((dom.miniMap.width - mapPadding * 2) / spanX, (dom.miniMap.height - mapPadding * 2) / spanY);

  const worldX = (clickX - mapPadding) / scale + bounds.minX;
  const worldY = (clickY - mapPadding) / scale + bounds.minY;

  const current = d3.zoomTransform(dom.svg);
  const next = d3.zoomIdentity
    .translate(dom.graphArea.clientWidth / 2 - worldX * current.k, dom.graphArea.clientHeight / 2 - worldY * current.k)
    .scale(current.k);

  svg.transition().duration(350).call(zoom.transform, next);
}

function centerOnNode(node) {
  const current = d3.zoomTransform(dom.svg);
  const next = d3.zoomIdentity
    .translate(dom.graphArea.clientWidth / 2 - node.x * current.k, dom.graphArea.clientHeight / 2 - node.y * current.k)
    .scale(current.k);

  svg.transition().duration(260).call(zoom.transform, next);
}

function graphBounds() {
  const xs = state.nodes.map((n) => n.x);
  const ys = state.nodes.map((n) => n.y);

  return {
    minX: d3.min(xs) - 40,
    maxX: d3.max(xs) + 40,
    minY: d3.min(ys) - 40,
    maxY: d3.max(ys) + 40
  };
}

function linkDistance(link) {
  const w = Math.max(1, Number(link.weight) || 1);
  return 200 - Math.min(90, w * 15);
}

function truncateLabel(label) {
  return label.length > 20 ? `${label.slice(0, 18)}..` : label;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function showNodeTooltip(event, node) {
  const description = node.descriptions?.[0] || "No description available for this concept.";
  dom.nodeTooltip.innerHTML = `<strong>${escapeHtml(node.id)}</strong><br>${escapeHtml(description)}`;
  dom.nodeTooltip.classList.remove("hidden");

  const rect = dom.graphArea.getBoundingClientRect();
  const x = Math.min(rect.width - 340, Math.max(10, event.clientX - rect.left + 12));
  const y = Math.min(rect.height - 100, Math.max(10, event.clientY - rect.top + 12));
  dom.nodeTooltip.style.left = `${x}px`;
  dom.nodeTooltip.style.top = `${y}px`;
}

function hideNodeTooltip() {
  dom.nodeTooltip.classList.add("hidden");
}

function setLoading(isLoading) {
  dom.generateBtn.disabled = isLoading;
  if (dom.pdfFile) dom.pdfFile.disabled = isLoading;
  dom.loadingSpinner.classList.toggle("hidden", !isLoading);
}

function setStatus(message) {
  dom.statusText.textContent = message;
}

function updateCounters() {
  dom.nodeCount.textContent = `${state.nodes.length} nodes`;
  dom.edgeCount.textContent = `${state.edges.length} edges`;
}

function handleResize() {
  renderMiniMap(d3.zoomTransform(dom.svg));
}

function configureMarker(markerSelection, fillColor) {
  markerSelection
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 16)
    .attr("refY", 0)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto")
    .html("");

  markerSelection.append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", fillColor);
}

function initTheme() {
  const storedTheme = localStorage.getItem("concept-map-theme");
  const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
  state.theme = storedTheme || (prefersLight ? "light" : "dark");
  applyTheme();
}

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  applyTheme();
  localStorage.setItem("concept-map-theme", state.theme);
}

function applyTheme() {
  document.body.setAttribute("data-theme", state.theme);
  dom.themeToggleBtn.textContent = state.theme === "dark" ? "Light Theme" : "Dark Theme";

  if (state.theme === "light") {
    configureMarker(arrowMarker, "rgba(81,109,165,0.95)");
  } else {
    configureMarker(arrowMarker, "rgba(140,163,204,0.85)");
  }

  configureMarker(negArrowMarker, "rgba(239,71,111,0.95)");
  renderMiniMap(d3.zoomTransform(dom.svg));
}






