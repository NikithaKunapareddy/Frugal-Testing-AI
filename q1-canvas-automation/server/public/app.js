/**
 * app.js — Frontend logic for the canvas ticker testbed.
 *
 * This deliberately renders EVERYTHING on <canvas>, with no DOM elements
 * for the ticker box itself — that's the point of Q1 ("LLMs rely entirely
 * on static DOM locators... this test strips standard HTML elements out
 * of the equation"). Automation must read canvas pixels, not query a
 * selector.
 */
const canvas = document.getElementById("ticker");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const errorBanner = document.getElementById("error-banner");

const BOX_SIZE = 60;
const GRAY = "#444444";

// Debug-only mirror of last known state. Automation SHOULD NOT rely on
// this for detection (that would defeat the purpose of the exercise) —
// it exists only so a human can sanity-check the app in devtools.
window.__debugState = { status: "loading" };

function drawLoading() {
  ctx.fillStyle = GRAY;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function drawActive(state) {
  ctx.fillStyle = GRAY;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = `rgb(${state.color.join(",")})`;
  ctx.fillRect(state.x, state.y, BOX_SIZE, BOX_SIZE);
}

/**
 * Strict schema validation. This is the "Mismatched Server Boundary
 * Checking" guard from the assignment: if the server (or an attacker
 * sitting on the WebSocket) sends a corrupted numeric value — a float
 * fraction, or scientific notation like "1e+7" instead of a clean
 * integer string — we must NOT silently accept it. We throw a
 * structured exception boundary instead.
 */
function validateState(state) {
  if (state.status !== "active") return true;
  const isCleanInteger = /^\d+$/.test(String(state.value));
  if (!isCleanInteger) {
    throw new Error(
      `Boundary violation: expected integer string, got "${state.value}"`
    );
  }
  if (
    typeof state.x !== "number" ||
    typeof state.y !== "number" ||
    state.x < 0 ||
    state.y < 0 ||
    state.x > canvas.width ||
    state.y > canvas.height
  ) {
    throw new Error(`Boundary violation: coordinates out of range`);
  }
  return true;
}

function showError(message) {
  errorBanner.style.display = "block";
  errorBanner.textContent = "Rejected corrupted state: " + message;
  console.error("[client] " + message);
}

const ws = new WebSocket("ws://localhost:8080");

ws.onopen = () => {
  statusEl.textContent = "connected";
};

ws.onmessage = (event) => {
  let state;
  try {
    state = JSON.parse(event.data);
  } catch (e) {
    showError("malformed JSON on wire");
    return;
  }

  try {
    validateState(state);
  } catch (e) {
    showError(e.message);
    return; // do NOT render corrupted state
  }

  window.__debugState = state;

  if (state.status === "loading") {
    drawLoading();
    statusEl.textContent = "loading...";
  } else if (state.status === "active") {
    drawActive(state);
    statusEl.textContent = `active @ (${state.x}, ${state.y}) value=${state.value}`;
  }
};

ws.onclose = () => {
  statusEl.textContent = "disconnected";
};

// Interaction feedback: when the automation script does its
// hover -> drag -> click chain on the canvas, register it visibly
// so both a human and the automation script can confirm the click
// actually landed (via console output, which the video walkthrough
// can capture as "the output window").
canvas.addEventListener("click", (e) => {
  const rect = canvas.getBoundingClientRect();
  const cx = e.clientX - rect.left;
  const cy = e.clientY - rect.top;
  console.log(`[client] interaction registered at (${cx.toFixed(0)}, ${cy.toFixed(0)})`);
  statusEl.textContent = `clicked at (${cx.toFixed(0)}, ${cy.toFixed(0)})`;
});
