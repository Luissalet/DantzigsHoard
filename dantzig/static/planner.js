const $ = (id) => document.getElementById(id);
const node = (tag, text, cls) => {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
};
const labels = {
  optimal: "Óptimo demostrado",
  feasible: "Plan factible",
  infeasible: "Sin plan posible",
  unknown: "Búsqueda inconclusa",
};
let problem,
  epoch = 0,
  runs = [],
  busy = false;
const setDuration = (job, resource, value) =>
  Object.defineProperty(job.durations, resource, {
    value,
    writable: true,
    enumerable: true,
    configurable: true,
  });
function editable(value) {
  return (
    value &&
    typeof value.name === "string" &&
    typeof value.unit === "string" &&
    Array.isArray(value.resources) &&
    value.resources.every((r) => typeof r === "string") &&
    Array.isArray(value.jobs) &&
    value.jobs.every(
      (j) =>
        j &&
        typeof j.id === "string" &&
        j.durations &&
        typeof j.durations === "object" &&
        !Array.isArray(j.durations) &&
        Array.isArray(j.after),
    )
  );
}
const key = "dantzig.planner.v1";
function message(text, error = false) {
  $("notice").textContent = text;
  $("notice").className = error ? "error" : "";
}
async function api(path, body) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail;
    throw Error(
      Array.isArray(detail)
        ? detail
            .map((x) => `${x.loc.slice(1).join(" / ")}: ${x.msg}`)
            .join("; ")
        : String(detail || "No se pudo completar la operación"),
    );
  }
  return data;
}
function stash() {
  try {
    localStorage.setItem(key, JSON.stringify(problem));
  } catch {
    message(
      "El navegador no pudo guardar el borrador. Puedes exportarlo como documento.",
      true,
    );
  }
}
function changed() {
  epoch++;
  runs = [];
  $("results").hidden = true;
  message("Borrador modificado. Calcula para obtener un plan actualizado.");
  stash();
}
function number(value) {
  return value === "" ? null : Number(value);
}
function bind(input, read) {
  input.addEventListener("input", () => {
    read(input.value);
    changed();
  });
}
function cellInput(row, value, label, type, update) {
  const td = node("td");
  const input = node("input");
  input.type = type;
  input.value = value ?? "";
  input.setAttribute("aria-label", label);
  if (type === "number") {
    input.min = "0";
    input.step = "1";
  }
  bind(input, update);
  td.append(input);
  row.append(td);
  return input;
}
function render() {
  $("name").value = problem.name;
  $("unit").value = problem.unit;
  $("change").value = problem.family_change;
  $("horizon").value = problem.horizon ?? "";
  $("objective").value = problem.objective;
  $("resources").replaceChildren();
  for (const resource of problem.resources) {
    const group = node("div", undefined, "resource");
    const label = node("label", "Nombre del recurso");
    const input = node("input");
    input.value = resource;
    label.append(input);
    group.append(label);
    input.addEventListener("change", () => {
      const next = input.value.trim();
      if (!next || (problem.resources.includes(next) && next !== resource)) {
        input.value = resource;
        message("Cada recurso necesita un nombre distinto y no vacío.", true);
        return;
      }
      problem.resources = problem.resources.map((r) =>
        r === resource ? next : r,
      );
      for (const j of problem.jobs)
        if (Object.hasOwn(j.durations, resource)) {
          setDuration(j, next, j.durations[resource]);
          delete j.durations[resource];
        }
      changed();
      render();
    });
    const remove = node("button", "Retirar");
    remove.type = "button";
    remove.setAttribute("aria-label", `Retirar recurso ${resource}`);
    remove.disabled = problem.resources.length === 1;
    remove.onclick = () => {
      problem.resources = problem.resources.filter((r) => r !== resource);
      for (const j of problem.jobs) delete j.durations[resource];
      changed();
      render();
    };
    group.append(remove);
    $("resources").append(group);
  }
  const head = node("tr");
  for (const title of [
    "Pedido",
    "Familia",
    ...problem.resources.map((r) => `Duración · ${r}`),
    "Disponible desde",
    "Entrega deseada",
    "Límite obligatorio",
    "Peso del retraso",
    "Después de (IDs separados por comas)",
    "Acciones",
  ]) {
    const th = node("th", title);
    th.scope = "col";
    head.append(th);
  }
  $("jobs").querySelector("thead").replaceChildren(head);
  const body = $("jobs").querySelector("tbody");
  body.replaceChildren();
  problem.jobs.forEach((j, index) => {
    const row = node("tr");
    cellInput(
      row,
      j.id,
      `Identificador pedido ${index + 1}`,
      "text",
      (v) => (j.id = v),
    ).required = true;
    cellInput(
      row,
      j.family,
      `Familia pedido ${index + 1}`,
      "text",
      (v) => (j.family = v),
    );
    for (const r of problem.resources) {
      const input = cellInput(
        row,
        j.durations[r],
        `Duración pedido ${index + 1} en ${r}`,
        "number",
        (v) => {
          if (v === "") delete j.durations[r];
          else setDuration(j, r, Number(v));
        },
      );
      input.min = "1";
    }
    for (const [field, title] of [
      ["release", "Disponibilidad"],
      ["due", "Entrega deseada"],
      ["deadline", "Límite obligatorio"],
      ["weight", "Peso"],
    ]) {
      const input = cellInput(
        row,
        j[field],
        `${title} pedido ${index + 1}`,
        "number",
        (v) => (j[field] = number(v)),
      );
      if (field === "weight") {
        input.min = "1";
        input.required = true;
      }
      if (field === "release") input.required = true;
    }
    cellInput(
      row,
      j.after.join(", "),
      `Precedencias pedido ${index + 1}`,
      "text",
      (v) =>
        (j.after = v
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean)),
    ).className = "after";
    const td = node("td");
    const remove = node("button", "Retirar");
    remove.type = "button";
    remove.setAttribute("aria-label", `Retirar pedido ${index + 1}`);
    remove.onclick = () => {
      problem.jobs.splice(index, 1);
      changed();
      render();
    };
    td.append(remove);
    row.append(td);
    body.append(row);
  });
}
function install(value) {
  problem = structuredClone(value);
  epoch++;
  runs = [];
  $("results").hidden = true;
  render();
  stash();
}
function formValid() {
  if (!$("planner").reportValidity()) return false;
  if (!problem.jobs.length) {
    message("Añade al menos un pedido.", true);
    return false;
  }
  return true;
}
function setBusy(value) {
  busy = value;
  for (const id of ["compare", "save", "example", "import"])
    $(id).disabled = value;
  $("planner").querySelector("[type=submit]").disabled = value;
}
function drawPlan(run) {
  const r = run.result;
  const section = node("article", undefined, "plan");
  section.append(
    node(
      "h3",
      run.problem.objective === "tardiness_then_makespan"
        ? "Prioridad: entregas"
        : "Prioridad: tiempo total",
    ),
  );
  section.append(node("p", labels[r.status] || r.status, "status"));
  if (!r.schedule.length) {
    section.append(node("p", r.message));
    return section;
  }
  const summary = node("p", undefined, "summary");
  summary.append(
    node("span", `Retraso ponderado: ${r.weighted_tardiness} ${r.unit}`),
    node("span", `Finalización: ${r.makespan} ${r.unit}`),
    node("span", r.verified ? "Restricciones comprobadas" : "Sin comprobación"),
  );
  section.append(summary);
  const timeline = node("div", undefined, "timeline");
  timeline.setAttribute("aria-label", "Cronograma por recurso");
  const ticks = node("div", undefined, "ticks");
  for (let i = 0; i <= 4; i++)
    ticks.append(node("span", String(Math.round((i * r.makespan) / 4))));
  timeline.append(ticks);
  for (const resource of run.problem.resources) {
    const lane = node("div", undefined, "lane");
    lane.append(node("span", resource));
    const track = node("div", undefined, "track");
    for (const row of r.schedule
      .filter((x) => x.resource === resource)
      .sort((a, b) => a.start - b.start)) {
      const bar = node("span", row.job, "bar");
      bar.style.left = `${(100 * row.start) / r.makespan}%`;
      bar.style.width = `${(100 * (row.end - row.start)) / r.makespan}%`;
      bar.title = `${row.job}: ${row.start}–${row.end} ${r.unit}`;
      track.append(bar);
    }
    lane.append(track);
    timeline.append(lane);
  }
  section.append(timeline);
  const wrap = node("div", undefined, "table-scroll");
  const table = node("table");
  const header = node("tr");
  for (const title of ["Pedido", "Recurso", "Inicio", "Fin", "Retraso"])
    header.append(node("th", title));
  const thead = node("thead");
  thead.append(header);
  table.append(thead);
  const tbody = node("tbody");
  for (const row of [...r.schedule].sort(
    (a, b) => a.start - b.start || a.job.localeCompare(b.job),
  )) {
    const tr = node("tr");
    const job = run.problem.jobs.find((j) => j.id === row.job);
    for (const v of [
      row.job,
      row.resource,
      row.start,
      row.end,
      job.due == null ? "—" : Math.max(0, row.end - job.due),
    ])
      tr.append(node("td", String(v)));
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
  section.append(wrap);
  section.append(node("p", r.scope, "help"));
  return section;
}
function showRuns(value) {
  runs = value;
  $("results").hidden = false;
  $("plans").replaceChildren(...runs.map(drawPlan));
  $("comparison").replaceChildren();
  const [a, b] = runs;
  if (a?.result.schedule.length && b?.result.schedule.length) {
    $("comparison").append(
      node(
        "p",
        `Comparación: entregas → retraso ${a.result.weighted_tardiness}, fin ${a.result.makespan}; tiempo total → retraso ${b.result.weighted_tardiness}, fin ${b.result.makespan}. Unidad: ${a.result.unit}.`,
      ),
    );
  }
}
async function calculate(compare = false) {
  if (busy || !formValid()) return;
  const snapshot = structuredClone(problem),
    version = epoch;
  setBusy(true);
  message(compare ? "Calculando las dos prioridades…" : "Calculando plan…");
  try {
    const objectives = compare
      ? ["tardiness_then_makespan", "makespan_then_tardiness"]
      : [snapshot.objective];
    const results = [];
    for (const objective of objectives)
      results.push(
        await api("/api/solve", {
          problem: { ...snapshot, objective },
          seconds: Number($("seconds").value),
        }),
      );
    if (epoch === version) {
      showRuns(results);
      message("Cálculo guardado con sus condiciones originales.");
    } else
      message(
        "Cálculo guardado en el historial. El borrador cambió: calcula de nuevo para actualizar el resultado.",
      );
    await history();
  } catch (e) {
    message(e.message, true);
  } finally {
    setBusy(false);
  }
}
function download(value, name) {
  const blob = new Blob([JSON.stringify(value, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = node("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function history() {
  const items = (await api("/api/records")).filter(item => ["problem", "run"].includes(item.kind));
  const target = $("history");
  target.replaceChildren();
  if (!items.length) {
    target.append(node("p", "Todavía no hay documentos guardados.", "help"));
    return;
  }
  for (const item of items) {
    const row = node("div", undefined, "history-row");
    const label = node("div", item.name);
    label.append(
      node(
        "small",
        `${item.kind === "run" ? "Cálculo" : "Problema"} · ${item.created} UTC`,
      ),
    );
    const open = node("button", "Abrir");
    open.type = "button";
    open.onclick = async () => {
      try {
        if (busy) return;
        const version = epoch;
        const record = await api("/api/records/" + encodeURIComponent(item.id));
        const input = record.kind === "run" ? record.problem : record;
        const clean = await api(
          "/api/validate",
          input.kind
            ? Object.fromEntries(
                Object.entries(input).filter(
                  ([k]) => !["id", "kind"].includes(k),
                ),
              )
            : input,
        );
        if (version !== epoch) {
          message(
            "El borrador cambió durante la recuperación. Vuelve a abrir el documento para sustituirlo.",
          );
          return;
        }
        install(clean);
        if (record.kind === "run") showRuns([record]);
        message("Documento recuperado. Puedes editar una nueva versión.");
        $("name").focus();
      } catch (e) {
        message(e.message, true);
      }
    };
    row.append(label, open);
    target.append(row);
  }
}
for (const [id, field] of [
  ["name", "name"],
  ["unit", "unit"],
  ["change", "family_change"],
  ["horizon", "horizon"],
  ["objective", "objective"],
])
  bind(
    $(id),
    (v) =>
      (problem[field] = ["change", "horizon"].includes(id) ? number(v) : v),
  );
$("planner").onsubmit = (e) => {
  e.preventDefault();
  calculate();
};
$("compare").onclick = () => calculate(true);
$("add-resource").onclick = () => {
  let i = problem.resources.length + 1;
  while (problem.resources.includes(`Recurso ${i}`)) i++;
  problem.resources.push(`Recurso ${i}`);
  changed();
  render();
};
$("add-job").onclick = () => {
  let i = problem.jobs.length + 1;
  while (problem.jobs.some((j) => j.id === `P${i}`)) i++;
  problem.jobs.push({
    id: `P${i}`,
    durations: {},
    release: 0,
    due: null,
    deadline: null,
    weight: 1,
    family: "",
    after: [],
  });
  changed();
  render();
};
$("save").onclick = async () => {
  if (busy || !formValid()) return;
  setBusy(true);
  try {
    await api("/api/problems", structuredClone(problem));
    await history();
    message("Problema guardado como un nuevo documento.");
  } catch (e) {
    message(e.message, true);
  } finally {
    setBusy(false);
  }
};
$("example").onclick = async () => {
  try {
    install(await api("/api/example"));
    message(
      "Ejemplo inventado cargado: seis pedidos, dos máquinas y cambio de familia.",
    );
  } catch (e) {
    message(e.message, true);
  }
};
$("export-problem").onclick = () => download(problem, "dantzig-problema.json");
$("export-run").onclick = () =>
  download(runs.length === 1 ? runs[0] : runs, "dantzig-resultados.json");
$("refresh").onclick = () => history().catch((e) => message(e.message, true));
$("import").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const version = epoch;
    const value = JSON.parse(await file.text());
    const input = value.kind === "run" || value.result ? value.problem : value;
    const clean = await api(
      "/api/validate",
      Object.fromEntries(
        Object.entries(input).filter(([k]) => !["id", "kind"].includes(k)),
      ),
    );
    if (version !== epoch) {
      message(
        "El borrador cambió durante la importación. Vuelve a importar para sustituirlo.",
      );
      return;
    }
    install(clean);
    message(
      "Problema importado. Calcula para obtener un resultado actualizado.",
    );
  } catch (error) {
    message("No se pudo importar: " + error.message, true);
  } finally {
    e.target.value = "";
  }
};
try {
  let restored;
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (!editable(parsed)) throw Error("Formato de borrador desconocido");
      restored = parsed;
    }
  } catch {
    try {
      const raw = localStorage.getItem(key);
      if (raw) localStorage.setItem(key + ".recovery", raw);
    } catch {}
    message(
      "No se pudo interpretar el borrador anterior. Se ha conservado una copia de recuperación en este navegador.",
      true,
    );
  }
  install(restored || (await api("/api/example")));
  await history();
} catch (error) {
  message(
    "No se pudo cargar la aplicación: " +
      error.message +
      ". Recarga para reintentar.",
    true,
  );
}
