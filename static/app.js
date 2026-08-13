const log = document.getElementById("log");
const form = document.getElementById("composer");
const input = document.getElementById("messageInput");
const resetBtn = document.getElementById("resetBtn");

function addBubble(role, text) {
  const el = document.createElement("div");
  el.className = `bubble ${role}`;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function addTyping() {
  const el = document.createElement("div");
  el.className = "typing";
  el.textContent = "Working on it…";
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function addActionCard(actionName, actionInput) {
  const card = document.createElement("div");
  card.className = "action-card";
  card.innerHTML = `
    <div class="action-title">Confirm action: ${actionName}</div>
    <pre>${JSON.stringify(actionInput, null, 2)}</pre>
    <div class="actions">
      <button class="confirm">Confirm</button>
      <button class="cancel">Cancel</button>
    </div>
  `;
  log.appendChild(card);
  log.scrollTop = log.scrollHeight;

  const confirmBtn = card.querySelector(".confirm");
  const cancelBtn = card.querySelector(".cancel");

  const finish = (approved) => {
    confirmBtn.disabled = true;
    cancelBtn.disabled = true;
    card.classList.add("resolved");
    sendConfirm(approved);
  };

  confirmBtn.addEventListener("click", () => finish(true));
  cancelBtn.addEventListener("click", () => finish(false));
}

function setComposerEnabled(enabled) {
  input.disabled = !enabled;
  form.querySelector("button").disabled = !enabled;
}

async function handleResponse(res) {
  const data = await res.json();
  if (!res.ok) {
    addBubble("error", data.error || "Something went wrong.");
    setComposerEnabled(true);
    return;
  }
  if (data.type === "pending_action") {
    addActionCard(data.action_name, data.action_input);
    // composer stays disabled until the pending action is resolved
  } else {
    addBubble("assistant", data.text);
    setComposerEnabled(true);
    input.focus();
  }
}

async function sendConfirm(approved) {
  const typing = addTyping();
  try {
    const res = await fetch("/api/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    });
    typing.remove();
    await handleResponse(res);
  } catch (err) {
    typing.remove();
    addBubble("error", "Network error talking to the server.");
    setComposerEnabled(true);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  addBubble("user", message);
  input.value = "";
  setComposerEnabled(false);

  const typing = addTyping();
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    typing.remove();
    await handleResponse(res);
  } catch (err) {
    typing.remove();
    addBubble("error", "Network error talking to the server.");
    setComposerEnabled(true);
  }
});

resetBtn.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  log.innerHTML = "";
  setComposerEnabled(true);
  input.focus();
});
