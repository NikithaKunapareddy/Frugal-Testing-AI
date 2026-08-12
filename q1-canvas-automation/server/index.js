/**
 * server/index.js
 * -----------------------------------------------------------------------
 * A tiny "ground truth" ticker server. This represents the real backend —
 * it streams state updates at a normal, undelayed cadence. All the jitter /
 * latency injection required by Q1 happens on the AUTOMATION side (see
 * automation/test.js), using Playwright's page.routeWebSocket(), NOT here.
 * That's intentional: the assignment wants YOU (the test) to be the one
 * hooking the network layer, not the app under test.
 * -----------------------------------------------------------------------
 */
const express = require("express");
const path = require("path");
const { WebSocketServer } = require("ws");
const http = require("http");

const app = express();
app.use(express.static(path.join(__dirname, "public")));

const httpServer = http.createServer(app);
const PORT = process.env.PORT || 3005;
httpServer.listen(PORT, () => {
  console.log(`[server] static site: http://localhost:${PORT}`);
});

// Separate raw WebSocket server = the "real" ticker feed.
// The browser will NOT connect to this directly — it connects to
// ws://localhost:8080, which Playwright intercepts via routeWebSocket()
// and re-establishes a connection to this same port as the "upstream".
const wss = new WebSocketServer({ port: 8080 });
console.log("[server] ticker feed: ws://localhost:8080");

const CANVAS_W = 400;
const CANVAS_H = 300;
const BOX_SIZE = 60;

function randomActiveState() {
  return {
    type: "state",
    status: "active",
    x: Math.floor(Math.random() * (CANVAS_W - BOX_SIZE)),
    y: Math.floor(Math.random() * (CANVAS_H - BOX_SIZE)),
    color: [
      40 + Math.floor(Math.random() * 180),
      40 + Math.floor(Math.random() * 180),
      40 + Math.floor(Math.random() * 180),
    ],
    // "value" simulates a ticker price in integer cents.
    // The frontend enforces this MUST be an integer string — see
    // public/app.js validateState(). This is what Q1's "Mismatched
    // Server Boundary Checking" step targets.
    value: String(1000 + Math.floor(Math.random() * 9000)),
  };
}

wss.on("connection", (socket) => {
  console.log("[server] client connected");

  // 1) Start in loading state (gray canvas).
  socket.send(JSON.stringify({ type: "state", status: "loading" }));

  // 2) After a short, realistic delay, flip to active with real data.
  //    (No artificial 8s+ delays here — that's injected by the automation
  //    layer, not the backend.)
  const toActive = setTimeout(() => {
    if (socket.readyState === socket.OPEN) {
      socket.send(JSON.stringify(randomActiveState()));
    }
  }, 600 + Math.random() * 400);

  // 3) Keep streaming fresh ticks every couple seconds, like a real feed.
  const interval = setInterval(() => {
    if (socket.readyState === socket.OPEN) {
      socket.send(JSON.stringify(randomActiveState()));
    }
  }, 2500);

  socket.on("close", () => {
    clearTimeout(toActive);
    clearInterval(interval);
    console.log("[server] client disconnected");
  });
});
