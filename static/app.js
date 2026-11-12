const form = document.getElementById("sim-form");
const llInput = document.getElementById("LL");
const clInput = document.getElementById("CL");
const errorBox = document.getElementById("error-box");
const canvas = document.getElementById("plot-canvas");
const tooltip = document.getElementById("tooltip");
const downloadBtn = document.getElementById("download-btn");

let lastResult = null;
let plotGeometry = null;

function getSelectedLoad() {
  return form.querySelector('input[name="load_type"]:checked').value;
}

function updateLoadInputs() {
  const isInductive = getSelectedLoad() === "inductive";
  llInput.disabled = !isInductive;
  clInput.disabled = isInductive;
}

form.querySelectorAll('input[name="load_type"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    updateLoadInputs();
    runSimulation();
  });
});

function formatSci(val, unit) {
  if (!Number.isFinite(val)) return "—";
  const abs = Math.abs(val);
  const str = abs !== 0 && (abs >= 1e4 || abs < 1e-2) ? val.toExponential(3) : val.toFixed(4);
  return unit ? `${str} ${unit}` : str;
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function niceStep(range, targetTicks) {
  if (range <= 0) return 1;
  const rough = range / targetTicks;
  const pow = Math.pow(10, Math.floor(Math.log10(rough)));
  const frac = rough / pow;
  let nice;
  if (frac <= 1) nice = 1;
  else if (frac <= 2) nice = 2;
  else if (frac <= 5) nice = 5;
  else nice = 10;
  return nice * pow;
}

function drawPlot(data, hoverIdx = null) {
  if (!data) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(300, Math.floor(rect.width));
  const height = Math.max(260, Math.floor(rect.height));

  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  const pad = { top: 38, right: 24, bottom: 52, left: 68 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const t = data.t_norm;
  const v = data.V_input;
  const params = data.params;

  const xMin = 0;
  const xMax = t[t.length - 1];

  let yMin = Math.min(...v, params.V1_plus, params.V_steady);
  let yMax = Math.max(...v, params.V1_plus, params.V_steady);
  const span = yMax - yMin || Math.abs(yMax) || 1;
  yMin -= 0.08 * span;
  yMax += 0.08 * span;

  const xToPx = (xv) => pad.left + ((xv - xMin) / (xMax - xMin || 1)) * plotW;
  const yToPx = (yv) => pad.top + ((yMax - yv) / (yMax - yMin || 1)) * plotH;

  plotGeometry = { pad, plotW, plotH, xMin, xMax, yMin, yMax, xToPx, yToPx };

  // Title
  ctx.fillStyle = "#1565c0";
  ctx.font = "600 14px 'Segoe UI', sans-serif";
  ctx.textAlign = "center";
  const loadLabel =
    getSelectedLoad() === "inductive"
      ? `Inductive Load (LL = ${Number(llInput.value).toExponential(2)} H)`
      : `Capacitive Load (CL = ${Number(clInput.value).toExponential(2)} F)`;
  ctx.fillText(`Input Terminal Transient Voltage V(0, t) — ${loadLabel}`, pad.left + plotW / 2, 22);

  // Vertical grid at multiples of T
  const xStep = niceStep(xMax - xMin, 10);
  ctx.strokeStyle = "#e6ebf2";
  ctx.lineWidth = 1;
  ctx.font = "11px 'Segoe UI', sans-serif";
  ctx.fillStyle = "#4b5563";
  ctx.textAlign = "center";

  for (let xt = 0; xt <= xMax + 1e-9; xt += xStep) {
    const px = xToPx(xt);
    ctx.beginPath();
    ctx.moveTo(px, pad.top);
    ctx.lineTo(px, pad.top + plotH);
    ctx.stroke();
    const label = Math.abs(xt - Math.round(xt)) < 1e-6 ? `${Math.round(xt)}T` : `${xt.toFixed(2)}T`;
    ctx.fillText(xt === 0 ? "0" : label, px, pad.top + plotH + 17);
  }

  // Highlight round-trip arrival markers (2T, 4T, ...) when reasonably spaced
  if (xMax >= 2 && xMax <= 40) {
    ctx.save();
    ctx.setLineDash([3, 4]);
    ctx.strokeStyle = "#cbd5e1";
    for (let k = 2; k <= xMax + 1e-9; k += 2) {
      const px = xToPx(k);
      ctx.beginPath();
      ctx.moveTo(px, pad.top);
      ctx.lineTo(px, pad.top + plotH);
      ctx.stroke();
    }
    ctx.restore();
  }

  // Horizontal grid
  const yStep = niceStep(yMax - yMin, 7);
  const yStart = Math.ceil(yMin / yStep) * yStep;
  ctx.textAlign = "right";
  for (let yt = yStart; yt <= yMax + 1e-9; yt += yStep) {
    const py = yToPx(yt);
    ctx.strokeStyle = "#e6ebf2";
    ctx.beginPath();
    ctx.moveTo(pad.left, py);
    ctx.lineTo(pad.left + plotW, py);
    ctx.stroke();
    ctx.fillStyle = "#4b5563";
    ctx.fillText(Math.abs(yt) < 1e-12 ? "0" : yt.toFixed(2), pad.left - 8, py + 4);
  }

  // Reference lines: V1+ and steady state
  ctx.save();
  ctx.setLineDash([6, 4]);
  ctx.strokeStyle = "#ef6c00";
  ctx.lineWidth = 1.2;
  const pyV1 = yToPx(params.V1_plus);
  ctx.beginPath();
  ctx.moveTo(pad.left, pyV1);
  ctx.lineTo(pad.left + plotW, pyV1);
  ctx.stroke();

  ctx.strokeStyle = "#2e7d32";
  const pyVss = yToPx(params.V_steady);
  ctx.beginPath();
  ctx.moveTo(pad.left, pyVss);
  ctx.lineTo(pad.left + plotW, pyVss);
  ctx.stroke();
  ctx.restore();

  // Plot border
  ctx.strokeStyle = "#94a3b8";
  ctx.lineWidth = 1.2;
  ctx.strokeRect(pad.left, pad.top, plotW, plotH);

  // Waveform polyline
  ctx.save();
  ctx.beginPath();
  ctx.rect(pad.left, pad.top, plotW, plotH);
  ctx.clip();

  ctx.strokeStyle = getSelectedLoad() === "inductive" ? "#1565c0" : "#c62828";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  for (let i = 0; i < t.length; i++) {
    const px = xToPx(t[i]);
    const py = yToPx(v[i]);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();
  ctx.restore();

  // Axis titles
  ctx.fillStyle = "#1b2430";
  ctx.font = "600 12px 'Segoe UI', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Time t (multiples of T = l / u)", pad.left + plotW / 2, height - 12);

  ctx.save();
  ctx.translate(18, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Input Voltage V(0, t) [V]", 0, 0);
  ctx.restore();

  // Legend
  const legendX = pad.left + plotW - 190;
  const legendY = pad.top + 10;
  ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
  ctx.strokeStyle = "#d9e0ea";
  ctx.lineWidth = 1;
  ctx.fillRect(legendX, legendY, 180, 62);
  ctx.strokeRect(legendX, legendY, 180, 62);

  const items = [
    { color: getSelectedLoad() === "inductive" ? "#1565c0" : "#c62828", dash: [], text: "V(0, t)" },
    { color: "#ef6c00", dash: [6, 4], text: `V1+ = ${params.V1_plus.toFixed(3)} V` },
    { color: "#2e7d32", dash: [6, 4], text: `V(0, inf) = ${params.V_steady.toFixed(3)} V` },
  ];
  ctx.font = "11px 'Segoe UI', sans-serif";
  ctx.textAlign = "left";
  items.forEach((item, idx) => {
    const y = legendY + 16 + idx * 18;
    ctx.save();
    ctx.setLineDash(item.dash);
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(legendX + 10, y - 3);
    ctx.lineTo(legendX + 34, y - 3);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = "#1b2430";
    ctx.fillText(item.text, legendX + 42, y);
  });

  // Hover marker
  if (hoverIdx !== null && hoverIdx >= 0 && hoverIdx < t.length) {
    const hx = xToPx(t[hoverIdx]);
    const hy = yToPx(v[hoverIdx]);
    ctx.save();
    ctx.strokeStyle = "#64748b";
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(hx, pad.top);
    ctx.lineTo(hx, pad.top + plotH);
    ctx.stroke();
    ctx.fillStyle = "#111827";
    ctx.beginPath();
    ctx.arc(hx, hy, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

async function runSimulation() {
  clearError();
  const payload = {
    V0: form.V0.value.trim(),
    Rg: form.Rg.value.trim(),
    l: form.l.value.trim(),
    u: form.u.value.trim(),
    R0: form.R0.value.trim(),
    X0: form.X0.value.trim(),
    load_type: getSelectedLoad(),
    LL: llInput.value.trim(),
    CL: clInput.value.trim(),
    t_max_T: form.t_max_T.value.trim(),
  };

  try {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || "Simulation failed.");
      return;
    }

    lastResult = data;
    const p = data.params;
    document.getElementById("m-T").textContent = formatSci(p.T, "s");
    document.getElementById("m-Zeff").textContent = formatSci(p.Zeff, "Ω");
    document.getElementById("m-GammaS").textContent = p.GammaS.toFixed(4);
    document.getElementById("m-V1").textContent = formatSci(p.V1_plus, "V");
    document.getElementById("m-tau").textContent = formatSci(p.tau, "s");
    document.getElementById("m-Vss").textContent = formatSci(p.V_steady, "V");

    drawPlot(lastResult);
  } catch (err) {
    showError("Could not reach backend server.");
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  runSimulation();
});

canvas.addEventListener("mousemove", (e) => {
  if (!lastResult || !plotGeometry) return;
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const { pad, plotW, plotH, xMin, xMax } = plotGeometry;

  if (mx < pad.left || mx > pad.left + plotW || my < pad.top || my > pad.top + plotH) {
    tooltip.hidden = true;
    drawPlot(lastResult);
    return;
  }

  const tTarget = xMin + ((mx - pad.left) / plotW) * (xMax - xMin);
  const tArr = lastResult.t_norm;
  const idx = Math.min(
    tArr.length - 1,
    Math.max(0, Math.round((tTarget / (xMax || 1)) * (tArr.length - 1)))
  );

  const tMult = tArr[idx];
  const tSec = tMult * lastResult.params.T;
  const volt = lastResult.V_input[idx];

  drawPlot(lastResult, idx);
  tooltip.hidden = false;
  tooltip.textContent = `t = ${tMult.toFixed(3)} T (${tSec.toExponential(2)} s) | V = ${volt.toFixed(4)} V`;
  const tx = Math.min(rect.width - 230, mx + 12);
  const ty = Math.max(8, my - 30);
  tooltip.style.left = `${tx}px`;
  tooltip.style.top = `${ty}px`;
});

canvas.addEventListener("mouseleave", () => {
  tooltip.hidden = true;
  if (lastResult) drawPlot(lastResult);
});

window.addEventListener("resize", () => {
  if (lastResult) drawPlot(lastResult);
});

downloadBtn.addEventListener("click", () => {
  if (!lastResult) return;
  const link = document.createElement("a");
  link.download = `V_input_${getSelectedLoad()}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
});

updateLoadInputs();
runSimulation();
