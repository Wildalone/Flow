const START = "agent_open";

const TREE = {
  agent_open: {
    speaker: "agent",
    text: "Hi, this is Alex from guest support — we've got a guest locked out at 42 Oak St (The Oak St Cottage). Want me to check what's going on and handle it?",
    choices: [{ label: "Continue →", next: "client_ok" }],
  },
  client_ok: {
    speaker: "client",
    text: "Yes, please go ahead and take care of it.",
    choices: [{ label: "Continue →", next: "agent_branch" }],
  },
  agent_branch: {
    speaker: "agent",
    text: "Checking the smart lock now... here's what I find:",
    choicesLabel: "What does the agent find?",
    choices: [
      { label: "✅ Lock is online — reset it remotely", next: "agent_online" },
      { label: "⚠️ Lock is offline — can't reset remotely", next: "agent_offline" },
      { label: "⚠️ No smart lock on file for this property", next: "agent_nolock" },
      { label: "❌ Address doesn't match any booking on file", next: "agent_clarify" },
    ],
  },

  // Branch 1: online lock, quick resolve
  agent_online: {
    speaker: "agent",
    text: "Lock is online — resetting it remotely right now.",
    choices: [{ label: "Continue →", next: "client_online_thanks" }],
  },
  client_online_thanks: {
    speaker: "client",
    text: "Great, thanks for handling that so quickly!",
    choices: [{ label: "Continue →", next: "end_resolved_reset" }],
  },
  end_resolved_reset: {
    speaker: "agent",
    text: "Glad that's sorted. Logging this incident and confirming with the guest that they're back in.",
    end: "resolved",
    endLabel: "Resolved",
    logIncident: {
      property_id: "prop_a",
      booking_id: "bk_1001",
      resolution: "resolved_remote_reset",
      summary: "Guest locked out at 42 Oak St. Smart lock was online — client authorized a remote reset, resolved immediately.",
    },
    choices: [],
  },

  // Branch 2/3: offline or no lock -> dispatch backup key
  agent_offline: {
    speaker: "agent",
    text: "Lock is offline — I can't reset it remotely. Want me to dispatch the backup-key holder?",
    choices: [{ label: "Continue →", next: "client_waiting_key" }],
  },
  agent_nolock: {
    speaker: "agent",
    text: "This property doesn't have a smart lock on file. Want me to dispatch the backup-key holder?",
    choices: [{ label: "Continue →", next: "client_waiting_key" }],
  },
  client_waiting_key: {
    speaker: "client",
    text: "Yes, please. Let me know once they're in touch.",
    choicesLabel: "Does the key holder respond?",
    choices: [
      { label: "✅ Key holder confirms — 10 minutes out", next: "client_key_coming" },
      { label: "⚠️ No response from the key holder", next: "agent_escalate" },
    ],
  },
  client_key_coming: {
    speaker: "client",
    text: "Sounds good, thanks for the update.",
    choices: [{ label: "Continue →", next: "end_resolved_key" }],
  },
  end_resolved_key: {
    speaker: "agent",
    text: "The key holder let the guest in. Logging this incident now.",
    end: "resolved",
    endLabel: "Resolved",
    logIncident: {
      property_id: "prop_a",
      booking_id: "bk_1001",
      resolution: "resolved_backup_key",
      summary: "Guest locked out at 42 Oak St. No remote reset available — client authorized dispatching the backup key holder, who responded and let the guest in.",
    },
    choices: [],
  },

  // Escalation
  agent_escalate: {
    speaker: "agent",
    text: "I'm not able to reach the backup-key holder. I don't want to leave the guest waiting on a false promise — want to reach out to them directly?",
    choices: [{ label: "Continue →", next: "client_escalate_reply" }],
  },
  client_escalate_reply: {
    speaker: "client",
    text: "Yes, I'll call them directly right now.",
    choices: [{ label: "Continue →", next: "end_escalated" }],
  },
  end_escalated: {
    speaker: "agent",
    text: "Logging this as an escalated incident, and letting the guest know honestly that you're following up personally instead of promising something that hasn't happened yet.",
    end: "escalated",
    endLabel: "Escalated — client following up directly",
    logIncident: {
      property_id: "prop_a",
      booking_id: "bk_1001",
      resolution: "escalated_no_response",
      summary: "Guest locked out at 42 Oak St. Backup key holder unreachable — escalated for the client to personally follow up instead of claiming it was resolved.",
    },
    choices: [],
  },

  // Branch 4: wrong / unmatched address
  agent_clarify: {
    speaker: "agent",
    text: "I couldn't find an active booking at that exact address the guest gave me. Could you confirm which property this actually is?",
    choicesLabel: "Does the client confirm the right property?",
    choices: [
      { label: "✅ Client confirms the correct address", next: "client_corrects" },
      { label: "❌ Client isn't sure either", next: "client_unsure" },
    ],
  },
  client_corrects: {
    speaker: "client",
    text: "Oh, that's actually 42 Oak St — the guest must have mentioned it wrong.",
    choices: [{ label: "Continue →", next: "agent_branch" }],
  },
  client_unsure: {
    speaker: "client",
    text: "I'm not sure either — let me check the reservation system and get back to you.",
    choices: [{ label: "Continue →", next: "end_needs_followup" }],
  },
  end_needs_followup: {
    speaker: "agent",
    text: "Understood — I'll hold off contacting the guest with a fix until we've confirmed which property this actually is, rather than guessing.",
    end: "followup",
    endLabel: "Needs client follow-up",
    logIncident: {
      property_id: null,
      booking_id: null,
      resolution: "escalated_no_booking_match",
      summary: "Guest reported a lockout but the address didn't match any booking, and the client couldn't confirm it either. Flagged for the client to follow up directly.",
    },
    choices: [],
  },
};

const SHORTCUTS = [
  { label: "Online lock", next: "agent_online" },
  { label: "Offline lock", next: "agent_offline" },
  { label: "No lock on file", next: "agent_nolock" },
  { label: "Wrong address", next: "agent_clarify" },
];

const log = document.getElementById("log");
const restartTopBtn = document.getElementById("restartTop");

function addTurn(node) {
  const turn = document.createElement("div");
  // Reuse the existing left/white vs right/orange style classes regardless of label text.
  const cssClass = node.speaker === "agent" ? "agent" : "guest";
  turn.className = `turn ${cssClass}`;

  const label = document.createElement("div");
  label.className = "speaker-label";
  label.textContent = node.speaker === "agent" ? "Agent" : "Client";
  turn.appendChild(label);

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = node.text;
  turn.appendChild(bubble);

  log.appendChild(turn);
}

function clearChoices() {
  document.querySelectorAll(".choices, .end-panel").forEach((el) => el.remove());
}

function showChoices(node) {
  clearChoices();
  const wrap = document.createElement("div");
  wrap.className = "choices";

  if (node.choicesLabel) {
    const label = document.createElement("div");
    label.className = "choices-label";
    label.textContent = node.choicesLabel;
    wrap.appendChild(label);
  }

  node.choices.forEach((choice) => {
    const btn = document.createElement("button");
    btn.className = "choice-btn";
    btn.type = "button";
    btn.textContent = choice.label;
    btn.addEventListener("click", () => selectChoice(choice.next));
    wrap.appendChild(btn);
  });

  log.appendChild(wrap);
  log.scrollTop = log.scrollHeight;
}

async function logIncident(payload) {
  try {
    await fetch("/api/log-incident", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    // Non-fatal for the walkthrough — the UI already shows the outcome either way.
  }
}

async function showEnd(node) {
  clearChoices();
  const wrap = document.createElement("div");
  wrap.className = "end-panel";

  const badge = document.createElement("div");
  badge.className = `end-badge ${node.end}`;
  badge.textContent = node.endLabel;
  wrap.appendChild(badge);

  const note = document.createElement("div");
  note.className = "log-note";
  note.textContent = "Logging incident…";
  wrap.appendChild(note);

  const shortcuts = document.createElement("div");
  shortcuts.className = "scenario-menu";
  const shortcutsLabel = document.createElement("div");
  shortcutsLabel.className = "scenario-menu-label";
  shortcutsLabel.textContent = "Try another path:";
  shortcuts.appendChild(shortcutsLabel);

  SHORTCUTS.forEach((s) => {
    const btn = document.createElement("button");
    btn.className = "scenario-btn";
    btn.type = "button";
    btn.textContent = s.label;
    btn.addEventListener("click", () => jumpTo(s.next));
    shortcuts.appendChild(btn);
  });
  wrap.appendChild(shortcuts);

  const restart = document.createElement("button");
  restart.className = "restart-btn";
  restart.type = "button";
  restart.textContent = "↺ Start over from the beginning";
  restart.addEventListener("click", start);
  wrap.appendChild(restart);

  log.appendChild(wrap);
  log.scrollTop = log.scrollHeight;

  if (node.logIncident) {
    await logIncident(node.logIncident);
    note.textContent = "✓ Logged to the incident record.";
  }
}

function selectChoice(nodeId) {
  const node = TREE[nodeId];
  addTurn(node);
  if (node.end) {
    showEnd(node);
  } else {
    showChoices(node);
  }
  log.scrollTop = log.scrollHeight;
}

function jumpTo(nodeId) {
  log.innerHTML = "";
  addTurn(TREE[START]);
  addTurn(TREE.client_ok);
  selectChoice(nodeId);
}

function start() {
  log.innerHTML = "";
  const node = TREE[START];
  addTurn(node);
  showChoices(node);
}

restartTopBtn.addEventListener("click", start);
start();
