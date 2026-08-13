const log = document.getElementById("log");
const composer = document.getElementById("composer");
const input = document.getElementById("messageInput");
const resetBtn = document.getElementById("resetBtn");

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
  label.textContent = kind === "assistant" ? "Guest (AI)" : "You (Host)";
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
  el.textContent = "Guest is typing…";
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

  const wrap = document.createElement("div");
  wrap.className = "scenario-menu";

  const label = document.createElement("div");
  label.className = "scenario-menu-label";
  label.textContent = "Pick a guest scenario — you'll play the host, the AI plays the guest:";
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
  addBubble("assistant", data.opening);
  composer.style.display = "flex";
  setComposerEnabled(true);
  input.focus();
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

resetBtn.addEventListener("click", async () => {
  await fetch("/api/persona/reset", { method: "POST" });
  showScenarioPicker();
});

showScenarioPicker();
