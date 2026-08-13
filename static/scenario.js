const START = "guest_open";

const TREE = {
  guest_open: {
    speaker: "guest",
    text: "Hi, I'm locked out of my rental at 42 Oak St! I've been standing outside for 10 minutes, please help.",
    choices: [{ label: "Continue →", next: "agent_lookup" }],
  },
  agent_lookup: {
    speaker: "agent",
    text: "Let me pull up your booking... Found it — you're checked in at The Oak St Cottage through the 16th. Checking the smart lock now.",
    choices: [{ label: "Continue →", next: "agent_branch" }],
  },
  agent_branch: {
    speaker: "agent",
    text: "Here's what I find when I check the property:",
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
    choices: [{ label: "Continue →", next: "guest_online_thanks" }],
  },
  guest_online_thanks: {
    speaker: "guest",
    text: "Oh, it just unlocked! Thank you so much!",
    choices: [{ label: "Continue →", next: "end_resolved_reset" }],
  },
  end_resolved_reset: {
    speaker: "agent",
    text: "Glad that's sorted. Logging this incident and sending you a quick confirmation message.",
    end: "resolved",
    endLabel: "Resolved",
    logIncident: {
      property_id: "prop_a",
      booking_id: "bk_1001",
      resolution: "resolved_remote_reset",
      summary: "Guest locked out at 42 Oak St. Smart lock was online — reset remotely, resolved immediately.",
    },
    choices: [],
  },

  // Branch 2/3: offline or no lock -> dispatch backup key
  agent_offline: {
    speaker: "agent",
    text: "Lock is offline — I can't reset it remotely. Dispatching your backup-key holder now.",
    choices: [{ label: "Continue →", next: "guest_waiting_key" }],
  },
  agent_nolock: {
    speaker: "agent",
    text: "This property doesn't have a smart lock on file — dispatching your backup-key holder now.",
    choices: [{ label: "Continue →", next: "guest_waiting_key" }],
  },
  guest_waiting_key: {
    speaker: "guest",
    text: "Okay... how long will that take? I'm getting cold out here.",
    choicesLabel: "Does the key holder respond?",
    choices: [
      { label: "✅ Key holder confirms — 10 minutes out", next: "guest_key_coming" },
      { label: "⚠️ No response from the key holder", next: "agent_escalate" },
    ],
  },
  guest_key_coming: {
    speaker: "guest",
    text: "Okay, thank you — I'll wait by the door.",
    choices: [{ label: "Continue →", next: "end_resolved_key" }],
  },
  end_resolved_key: {
    speaker: "agent",
    text: "The key holder let the guest in. Logging this incident and sending a follow-up message.",
    end: "resolved",
    endLabel: "Resolved",
    logIncident: {
      property_id: "prop_a",
      booking_id: "bk_1001",
      resolution: "resolved_backup_key",
      summary: "Guest locked out at 42 Oak St. No remote reset available — backup key holder dispatched and responded, guest let in.",
    },
    choices: [],
  },

  // Escalation
  agent_escalate: {
    speaker: "agent",
    text: "I'm not able to reach the backup-key holder. I won't leave you waiting on a false promise — I'm asking the host to call them directly right now.",
    choices: [{ label: "Continue →", next: "guest_escalate_reply" }],
  },
  guest_escalate_reply: {
    speaker: "guest",
    text: "Okay... please hurry, it's getting late.",
    choices: [{ label: "Continue →", next: "end_escalated" }],
  },
  end_escalated: {
    speaker: "agent",
    text: "Logging this as an escalated incident so the host follows up personally, and sending you an honest status update instead of a false all-clear.",
    end: "escalated",
    endLabel: "Escalated — host notified to call directly",
    logIncident: {
      property_id: "prop_a",
      booking_id: "bk_1001",
      resolution: "escalated_no_response",
      summary: "Guest locked out at 42 Oak St. Backup key holder unreachable — escalated to host for a direct call instead of claiming it was resolved.",
    },
    choices: [],
  },

  // Branch 4: wrong / unmatched address
  agent_clarify: {
    speaker: "agent",
    text: "I couldn't find an active booking at that exact address. Could you double-check it against your booking confirmation?",
    choicesLabel: "Does the guest confirm the right address?",
    choices: [
      { label: "✅ Guest gives the correct address", next: "guest_corrects" },
      { label: "❌ Guest still isn't sure", next: "guest_unsure" },
    ],
  },
  guest_corrects: {
    speaker: "guest",
    text: "Oh sorry — it's actually 42 Oak St, I misread my confirmation email!",
    choices: [{ label: "Continue →", next: "agent_lookup" }],
  },
  guest_unsure: {
    speaker: "guest",
    text: "I'm not sure... I booked through a friend's account.",
    choices: [{ label: "Continue →", next: "end_needs_followup" }],
  },
  end_needs_followup: {
    speaker: "agent",
    text: "I can't act without confirming which property this is — flagging this for the host to follow up personally rather than guessing.",
    end: "followup",
    endLabel: "Needs host follow-up",
    logIncident: {
      property_id: null,
      booking_id: null,
      resolution: "escalated_no_booking_match",
      summary: "Guest reported a lockout but the address didn't match any booking, and the guest couldn't confirm it. Flagged for the host to follow up directly.",
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
  turn.className = `turn ${node.speaker}`;

  const label = document.createElement("div");
  label.className = "speaker-label";
  label.textContent = node.speaker === "guest" ? "Guest" : "Agent";
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
  addTurn(TREE.agent_lookup);
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
