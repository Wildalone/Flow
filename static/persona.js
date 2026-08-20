const log = document.getElementById("log");
const composer = document.getElementById("composer");
const input = document.getElementById("messageInput");
const resetBtn = document.getElementById("resetBtn");
const wrapupBar = document.getElementById("wrapupBar");
const wrapupBtn = document.getElementById("wrapupBtn");

const SCENARIOS = [
  { id: "prop_a", label: "Online lock — 42 Oak St" },
  { id: "prop_b", label: "Offline lock — 118 Maple Ave" },
  { id: "prop_c", label: "No lock, unresponsive key holder — 7 Birch Court" },
];

function addBubble(kind, text) {
  if (kind === "error") {
    const el = document.createElement("div");
    el.className = "bubble error";
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return;
  }

  const turn = document.createElement("div");
  turn.className = `turn ${kind === "assistant" ? "guest" : "agent"}`;

  const label = document.createElement("div");
  label.className = "speaker-label";
  label.textContent = kind === "assistant" ? "Host (AI)" : "You (Agent)";
  turn.appendChild(label);

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  turn.appendChild(bubble);

  log.appendChild(turn);
  log.scrollTop = log.scrollHeight;
}

function addTyping() {
  const el = document.createElement("div");
  el.className = "typing";
  el.textContent = "Host is typing…";
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function setComposerEnabled(enabled) {
  input.disabled = !enabled;
  composer.querySelector("button").disabled = !enabled;
}

function showScenarioPicker() {
  log.innerHTML = "";
  composer.style.display = "none";
  wrapupBar.style.display = "none";

  const wrap = document.createElement("div");
  wrap.className = "scenario-menu";

  const label = document.createElement("div");
  label.className = "scenario-menu-label";
  label.textContent = "Pick a lockout scenario — you'll play the support agent, the AI plays the host you're messaging:";
  wrap.appendChild(label);

  SCENARIOS.forEach((s) => {
    const btn = document.createElement("button");
    btn.className = "scenario-btn";
    btn.type = "button";
    btn.textContent = s.label;
    btn.addEventListener("click", () => startScenario(s.id));
    wrap.appendChild(btn);
  });

  log.appendChild(wrap);
}

async function startScenario(propertyId) {
  const res = await fetch("/api/persona/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ property_id: propertyId }),
  });
  const data = await res.json();
  log.innerHTML = "";
  const hint = document.createElement("div");
  hint.className = "log-note";
  hint.style.alignSelf = "center";
  hint.textContent = `You message the host first — e.g. "${data.starter}"`;
  log.appendChild(hint);
  composer.style.display = "flex";
  wrapupBar.style.display = "flex";
  setComposerEnabled(true);
  input.focus();
}

async function wrapUp() {
  setComposerEnabled(false);
  wrapupBtn.disabled = true;
  const res = await fetch("/api/persona/end", { method: "POST" });
  const data = await res.json();
  composer.style.display = "none";
  wrapupBar.style.display = "none";

  if (!res.ok) {
    addBubble("error", data.error || "Something went wrong wrapping this up.");
    setComposerEnabled(true);
    wrapupBtn.disabled = false;
    return;
  }

  const panel = document.createElement("div");
  panel.className = "end-panel";
  const badge = document.createElement("div");
  badge.className = `end-badge ${data.end_class}`;
  badge.textContent = data.end_label;
  panel.appendChild(badge);
  const note = document.createElement("div");
  note.className = "log-note";
  note.textContent = "✓ Logged to the incident record.";
  panel.appendChild(note);
  const restart = document.createElement("button");
  restart.className = "restart-btn";
  restart.type = "button";
  restart.textContent = "↺ Try another scenario";
  restart.addEventListener("click", showScenarioPicker);
  panel.appendChild(restart);
  log.appendChild(panel);
  log.scrollTop = log.scrollHeight;
}

composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  addBubble("user", message);
  input.value = "";
  setComposerEnabled(false);

  const typing = addTyping();
  try {
    const res = await fetch("/api/persona/reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    typing.remove();
    const data = await res.json();
    if (!res.ok) {
      addBubble("error", data.error || "Something went wrong.");
    } else {
      addBubble("assistant", data.reply);
    }
  } catch (err) {
    typing.remove();
    addBubble("error", "Network error talking to the server.");
  }
  setComposerEnabled(true);
  input.focus();
});

wrapupBtn.addEventListener("click", wrapUp);

resetBtn.addEventListener("click", async () => {
  await fetch("/api/persona/reset", { method: "POST" });
  showScenarioPicker();
});

showScenarioPicker();
