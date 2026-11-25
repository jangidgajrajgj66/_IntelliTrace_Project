(() => {
  const state = {
    livePolling: true,
    pollTimer: null,
    thresholds: {
      max_response_time_ms: 300,
      max_error_rate_pct: 5,
      max_queue_length: 25,
    },
    incidents: [],
    selectedIncident: null,
  };

  const $ = (id) => document.getElementById(id);

  function showToast(message, type = "info") {
    const container = $("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3800);
  }

  async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  function drawLineChart(canvasId, values, threshold, color, unit) {
    const canvas = $(canvasId);
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(rect.width || 300, 220);
    const height = 150;
    canvas.width = width * dpr;
    canvas.height = height * dpr;

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const pad = { top: 14, right: 12, bottom: 20, left: 40 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;

    const data = values.length ? values : [0];
    const maxVal = Math.max(...data, threshold * 1.25, 1);

    // Grid lines
    ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
      const y = pad.top + (plotH * i) / 3;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(width - pad.right, y);
      ctx.stroke();

      const labelVal = Math.round(maxVal * (1 - i / 3));
      ctx.fillStyle = "#64748b";
      ctx.font = "10px monospace";
      ctx.fillText(`${labelVal}`, 4, y + 3);
    }

    // Threshold line
    const threshY = pad.top + plotH * (1 - threshold / maxVal);
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(244, 63, 94, 0.75)";
    ctx.beginPath();
    ctx.moveTo(pad.left, threshY);
    ctx.lineTo(width - pad.right, threshY);
    ctx.stroke();
    ctx.restore();

    if (data.length < 2) return;

    // Area fill
    const stepX = plotW / (data.length - 1);
    ctx.beginPath();
    data.forEach((v, idx) => {
      const x = pad.left + idx * stepX;
      const y = pad.top + plotH * (1 - Math.min(v, maxVal) / maxVal);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(pad.left + (data.length - 1) * stepX, pad.top + plotH);
    ctx.lineTo(pad.left, pad.top + plotH);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
    grad.addColorStop(0, `${color}33`);
    grad.addColorStop(1, `${color}00`);
    ctx.fillStyle = grad;
    ctx.fill();

    // Line stroke
    ctx.beginPath();
    data.forEach((v, idx) => {
      const x = pad.left + idx * stepX;
      const y = pad.top + plotH * (1 - Math.min(v, maxVal) / maxVal);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Latest point
    const lastVal = data[data.length - 1];
    const lastX = pad.left + (data.length - 1) * stepX;
    const lastY = pad.top + plotH * (1 - Math.min(lastVal, maxVal) / maxVal);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = lastVal > threshold ? "#f43f5e" : color;
    ctx.fill();

    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px monospace";
    ctx.fillText(`Latest: ${lastVal}${unit}`, pad.left, height - 4);
  }

  function updateKPIs(latest, serviceState) {
    if (!latest) return;
    const t = state.thresholds;
    const resp = Number(latest.response_time_ms || 0);
    const err = Number(latest.error_rate_pct || 0);
    const queue = Number(latest.queue_length || 0);

    $("val-resp").textContent = resp.toFixed(1);
    $("val-err").textContent = err.toFixed(2);
    $("val-queue").textContent = Math.round(queue);
    $("val-rps").textContent = Number(latest.throughput_rps || 0).toFixed(1);
    $("val-cpu-mem").textContent = `CPU ${Number(latest.cpu_percent || 0).toFixed(0)}% • RAM ${Number(latest.memory_percent || 0).toFixed(0)}%`;

    if (serviceState) {
      $("val-workers").textContent = serviceState.workers;
      $("val-config-ver").textContent = serviceState.config_version;
      $("val-active-scenario").textContent = serviceState.active_scenario
        ? `Fault: ${serviceState.active_scenario}`
        : "No active fault";

      const pill = $("system-health-pill");
      const text = $("system-health-text");
      if (serviceState.is_healthy) {
        pill.className = "status-pill nominal";
        text.textContent = "NOMINAL";
      } else {
        pill.className = "status-pill breach";
        text.textContent = "SLA BREACH";
      }
    }

    const setBar = (cardId, barId, val, limit) => {
      const pct = Math.min(100, Math.round((val / Math.max(limit * 1.5, 1)) * 100));
      const breached = val > limit;
      $(cardId).classList.toggle("breach", breached);
      const bar = $(barId);
      bar.style.width = `${Math.max(6, pct)}%`;
      bar.style.background = breached ? "var(--rose)" : "var(--cyan)";
    };

    setBar("kpi-card-resp", "bar-resp", resp, t.max_response_time_ms);
    setBar("kpi-card-err", "bar-err", err, t.max_error_rate_pct);
    setBar("kpi-card-queue", "bar-queue", queue, t.max_queue_length);
  }

  async function refreshTelemetry() {
    try {
      const data = await apiFetch("/api/v1/telemetry/history?limit=30");
      state.thresholds = data.thresholds || state.thresholds;
      const history = data.history || [];
      if (history.length > 0) {
        updateKPIs(history[history.length - 1], data.service_state);
        drawLineChart(
          "chart-resp",
          history.map((p) => p.response_time_ms),
          state.thresholds.max_response_time_ms,
          "#22d3ee",
          "ms"
        );
        drawLineChart(
          "chart-err",
          history.map((p) => p.error_rate_pct),
          state.thresholds.max_error_rate_pct,
          "#a855f7",
          "%"
        );
        drawLineChart(
          "chart-queue",
          history.map((p) => p.queue_length),
          state.thresholds.max_queue_length,
          "#38bdf8",
          ""
        );
      }
    } catch (err) {
      console.error("Telemetry refresh error:", err);
    }
  }

  async function refreshLogs() {
    try {
      const filter = $("log-filter").value;
      const data = await apiFetch("/api/v1/logs?limit=40");
      const container = $("log-stream");
      const logs = (data.logs || []).filter((l) => filter === "ALL" || l.level === filter);
      container.innerHTML = logs
        .map(
          (l) =>
            `<div class="log-line"><span style="color:#64748b">[${l.timestamp}]</span> <span class="log-lvl-${l.level}">[${l.level}]</span> ${escapeHtml(l.message)}</div>`
        )
        .join("");
    } catch (err) {
      console.error("Logs refresh error:", err);
    }
  }

  async function refreshTraffic() {
    try {
      const s = await apiFetch("/api/v1/traffic/status");
      $("tf-sent").textContent = s.requests_sent;
      $("tf-ok").textContent = s.success_count;
      $("tf-err").textContent = s.error_count;
      $("tf-lat").textContent = `${s.avg_latency_ms} ms`;
      $("traffic-badge").textContent = s.is_running ? `ACTIVE (${s.target_rps} RPS)` : "IDLE";
      $("btn-traffic-start").disabled = s.is_running;
      $("btn-traffic-stop").disabled = !s.is_running;
    } catch (err) {
      console.error("Traffic status error:", err);
    }
  }

  async function refreshIncidents() {
    try {
      const data = await apiFetch("/api/v1/incidents?limit=25");
      state.incidents = data.incidents || [];
      $("incidents-count").textContent = `${data.total || state.incidents.length} total`;
      const tbody = $("incidents-tbody");
      tbody.innerHTML = state.incidents
        .map((inc) => {
          const cls = inc.status === "RESOLVED" ? "resolved" : "escalated";
          return `
            <tr data-inc-id="${escapeHtml(inc.id)}">
              <td><code>${escapeHtml(inc.id)}</code></td>
              <td>${escapeHtml(inc.title || inc.scenario_id)}</td>
              <td>${escapeHtml(inc.root_cause || "--")}</td>
              <td><span class="status-tag ${cls}">${escapeHtml(inc.status)}</span></td>
              <td><code>${escapeHtml(inc.detection_timestamp || "")}</code></td>
            </tr>
          `;
        })
        .join("");

      tbody.querySelectorAll("tr").forEach((row) => {
        row.addEventListener("click", () => {
          const id = row.getAttribute("data-inc-id");
          const found = state.incidents.find((i) => i.id === id);
          if (found) renderHistoricalIncident(found);
        });
      });
    } catch (err) {
      console.error("Incidents refresh error:", err);
    }
  }

  function highlightPipeline(stations, finalStatus) {
    document.querySelectorAll(".pipe-node").forEach((node) => {
      const st = node.getAttribute("data-station");
      node.classList.toggle("visited", stations.includes(st));
    });
    const badge = $("pipeline-status-badge");
    if (!stations.length) {
      badge.textContent = "Idle — Monitoring";
    } else {
      badge.textContent = `Last Run: ${finalStatus}`;
    }
  }

  function renderDossier({
    incidentId,
    title,
    status,
    severity,
    rootCause,
    detectedAt,
    resolvedAt,
    explanation,
    handover,
    actions,
    beforeMetrics,
    afterMetrics,
    timeline,
  }) {
    $("dossier-empty").classList.add("hidden");
    $("dossier-content").classList.remove("hidden");

    $("dossier-subtitle").textContent = `${title} • ${incidentId}`;
    const badge = $("dossier-status-badge");
    badge.textContent = status;
    badge.className = `status-tag ${status === "RESOLVED" ? "resolved" : "escalated"}`;

    $("diag-id").textContent = incidentId;
    $("diag-root-cause").textContent = rootCause || "Unknown";
    $("diag-severity").textContent = severity || "CRITICAL";
    $("diag-timestamps").textContent = `Detected: ${detectedAt || "--"} | Closed: ${resolvedAt || "Open"}`;
    $("diag-explanation").textContent = explanation || "No briefing available.";

    if (handover) {
      $("diag-handover-box").classList.remove("hidden");
      $("diag-handover-text").textContent = handover;
    } else {
      $("diag-handover-box").classList.add("hidden");
    }

    // Actions table
    const actBody = $("actions-tbody");
    if (actions && actions.length) {
      actBody.innerHTML = actions
        .map(
          (a) => `
          <tr>
            <td>#${a.attempt_number}</td>
            <td><code>${escapeHtml(a.action_name)}</code></td>
            <td><code>${escapeHtml(JSON.stringify(a.parameters || {}))}</code></td>
            <td>${a.is_approved === false ? '<span class="status-tag escalated">BLOCKED</span>' : '<span class="status-tag resolved">APPROVED</span>'}</td>
            <td><span class="status-tag executed">${escapeHtml(a.status)}</span></td>
            <td>${escapeHtml(a.execution_message || "")}</td>
          </tr>
        `
        )
        .join("");
    } else {
      actBody.innerHTML = `<tr><td colspan="6" style="color:var(--text-muted)">No remediation actions recorded.</td></tr>`;
    }

    // Before vs After
    const bm = beforeMetrics || {};
    const am = afterMetrics || {};
    const metricsMeta = [
      { key: "response_time_ms", label: "Response Time", unit: "ms", limit: state.thresholds.max_response_time_ms },
      { key: "error_rate_pct", label: "Error Rate", unit: "%", limit: state.thresholds.max_error_rate_pct },
      { key: "queue_length", label: "Queue Backlog", unit: "reqs", limit: state.thresholds.max_queue_length },
    ];

    $("delta-grid").innerHTML = metricsMeta
      .map((m) => {
        const bVal = bm[m.key] !== undefined ? Number(bm[m.key]).toFixed(1) : "--";
        const aNum = am[m.key] !== undefined ? Number(am[m.key]) : null;
        const aVal = aNum !== null ? aNum.toFixed(1) : "--";
        const ok = aNum !== null && aNum <= m.limit;
        return `
          <div class="delta-card">
            <div class="delta-name">${m.label} (SLA &le; ${m.limit}${m.unit})</div>
            <div class="delta-vals">
              <span class="delta-before">${bVal}${m.unit}</span>
              <span>&rarr;</span>
              <span class="delta-after ${ok ? "ok" : "bad"}">${aVal}${m.unit}</span>
            </div>
          </div>
        `;
      })
      .join("");

    // Timeline
    const tlList = $("timeline-list");
    if (timeline && timeline.length) {
      tlList.innerHTML = timeline
        .map(
          (step) => `
          <div class="tl-item">
            <div class="tl-station">${escapeHtml(step.station || "STEP")}</div>
            <div class="tl-body">${escapeHtml(step.message || step.root_cause || step.action || step.reason || "Executed")}</div>
            <div class="tl-ts">${escapeHtml(step.timestamp || "")}</div>
          </div>
        `
        )
        .join("");
      highlightPipeline(
        timeline.map((s) => s.station),
        status
      );
    } else {
      tlList.innerHTML = `<div style="color:var(--text-muted)">Timeline persisted in SQLite audit log.</div>`;
      highlightPipeline(
        status === "ESCALATED"
          ? ["DETECT", "INVESTIGATE", "SAFETY_EVAL", "REMEDIATE", "VERIFY", "ESCALATE"]
          : ["DETECT", "INVESTIGATE", "SAFETY_EVAL", "REMEDIATE", "VERIFY"],
        status
      );
    }
  }

  function renderHistoricalIncident(inc) {
    renderDossier({
      incidentId: inc.id,
      title: inc.title || inc.scenario_id,
      status: inc.status,
      severity: inc.severity,
      rootCause: inc.root_cause,
      detectedAt: inc.detection_timestamp,
      resolvedAt: inc.resolution_timestamp,
      explanation: inc.explanation,
      handover: inc.status === "ESCALATED" ? inc.explanation : null,
      actions: inc.actions || [],
      beforeMetrics: inc.before_metrics,
      afterMetrics: inc.after_metrics,
      timeline: [],
    });
  }

  async function runScenario(scenarioId, btn) {
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Investigating...";
    try {
      const res = await apiFetch("/api/v1/scenarios/execute", {
        method: "POST",
        body: JSON.stringify({ scenario_id: scenarioId }),
      });
      renderDossier({
        incidentId: res.incident_id,
        title: res.title,
        status: res.status,
        severity: res.severity,
        rootCause: res.root_cause,
        detectedAt: res.detected_at,
        resolvedAt: res.resolved_at,
        explanation: res.explanation,
        handover: res.human_handover_notes,
        actions: res.actions_taken,
        beforeMetrics: res.before_metrics,
        afterMetrics: res.after_metrics,
        timeline: res.timeline,
      });
      showToast(`Incident ${res.incident_id}: ${res.status}`, res.status === "RESOLVED" ? "success" : "error");
      await Promise.all([refreshTelemetry(), refreshIncidents(), refreshLogs()]);
    } catch (err) {
      showToast(`Scenario failed: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  async function initMetadata() {
    try {
      const [info, health, scenarios] = await Promise.all([
        apiFetch("/api/v1/info"),
        apiFetch("/api/v1/health"),
        apiFetch("/api/v1/scenarios"),
      ]);

      $("llm-badge").textContent = `${info.llm_provider} (${info.llm_model})`;

      $("whitelist-pills").innerHTML = (health.approved_actions || [])
        .map((a) => `<span class="action-pill">${escapeHtml(a)}</span>`)
        .join("");

      const list = $("scenarios-list");
      list.innerHTML = Object.values(scenarios)
        .map(
          (sc) => `
          <div class="scenario-card">
            <div class="scenario-top">
              <div class="scenario-name">${escapeHtml(sc.name)}</div>
              <span class="scenario-outcome ${sc.resolvable ? "auto" : "escalate"}">
                ${sc.resolvable ? "Auto-Heal" : "Human Escalation"}
              </span>
            </div>
            <div class="scenario-desc">${escapeHtml(sc.description)}</div>
            <div class="scenario-symptoms">${escapeHtml(sc.symptoms)}</div>
            <button class="btn btn-primary btn-run-scenario" data-scenario="${escapeHtml(sc.id)}">
              Inject &amp; Investigate
            </button>
          </div>
        `
        )
        .join("");

      list.querySelectorAll(".btn-run-scenario").forEach((btn) => {
        btn.addEventListener("click", () => runScenario(btn.getAttribute("data-scenario"), btn));
      });
    } catch (err) {
      showToast(`Failed to load metadata: ${err.message}`, "error");
    }
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function bindEvents() {
    // Tabs
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        $(btn.getAttribute("data-tab")).classList.add("active");
      });
    });

    // Live polling toggle
    $("btn-live-toggle").addEventListener("click", () => {
      state.livePolling = !state.livePolling;
      $("live-dot").classList.toggle("active", state.livePolling);
      $("btn-live-toggle").innerHTML = `<span id="live-dot" class="live-dot ${state.livePolling ? "active" : ""}"></span> Live: ${state.livePolling ? "ON" : "OFF"}`;
    });

    // Manual tick
    $("btn-tick").addEventListener("click", async () => {
      await apiFetch("/api/v1/service/tick", { method: "POST" });
      await Promise.all([refreshTelemetry(), refreshLogs()]);
    });

    // Reset baseline
    $("btn-reset").addEventListener("click", async () => {
      await apiFetch("/api/v1/service/reset", { method: "POST" });
      highlightPipeline([], "Idle");
      showToast("Service restored to nominal baseline.", "success");
      await Promise.all([refreshTelemetry(), refreshLogs()]);
    });

    // Traffic controls
    $("rps-slider").addEventListener("input", (e) => {
      $("rps-value").textContent = e.target.value;
    });

    $("btn-traffic-start").addEventListener("click", async () => {
      const rps = Number($("rps-slider").value);
      await apiFetch("/api/v1/traffic/start", {
        method: "POST",
        body: JSON.stringify({ target_rps: rps }),
      });
      showToast(`Traffic generator started at ${rps} RPS`, "success");
      await refreshTraffic();
    });

    $("btn-traffic-stop").addEventListener("click", async () => {
      await apiFetch("/api/v1/traffic/stop", { method: "POST" });
      showToast("Traffic generator stopped.");
      await refreshTraffic();
    });

    // Safety policy validator
    $("btn-validate-policy").addEventListener("click", async () => {
      const actionName = $("policy-action-input").value.trim();
      if (!actionName) return;
      const res = await apiFetch("/api/v1/safety/validate", {
        method: "POST",
        body: JSON.stringify({ incident_id: "POLICY-CHECK", action_name: actionName, parameters: {} }),
      });
      const box = $("policy-result");
      box.classList.remove("hidden", "ok", "blocked");
      box.classList.add(res.is_approved ? "ok" : "blocked");
      box.textContent = `[${res.status_code}] ${res.reason}`;
    });

    $("log-filter").addEventListener("change", refreshLogs);
  }

  async function boot() {
    bindEvents();
    await initMetadata();
    await Promise.all([refreshTelemetry(), refreshIncidents(), refreshLogs(), refreshTraffic()]);
    state.pollTimer = setInterval(() => {
      if (state.livePolling) {
        refreshTelemetry();
        refreshLogs();
        refreshTraffic();
      }
    }, 2500);
  }

  boot();
})();

