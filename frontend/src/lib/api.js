import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, timeout: 30000 });

export const api = {
  listTickers: () => client.get("/tickers").then((r) => r.data),
  addTicker: (symbol) => client.post("/tickers", { symbol }).then((r) => r.data),
  deleteTicker: (symbol) => client.delete(`/tickers/${symbol}`).then((r) => r.data),
  updateOverrides: (symbol, overrides) =>
    client.put(`/tickers/${symbol}/overrides`, overrides).then((r) => r.data),
  getSettings: () => client.get("/settings").then((r) => r.data),
  updateSettings: (settings) => client.put("/settings", settings).then((r) => r.data),
  listAlerts: () => client.get("/alerts").then((r) => r.data),
  clearAlerts: () => client.delete("/alerts").then((r) => r.data),
  scanStatus: () => client.get("/scan/status").then((r) => r.data),
  runScan: () => client.post("/scan/run").then((r) => r.data),
  testNotification: () => client.post("/notifications/test").then((r) => r.data),
  getVapidKey: () => client.get("/push/vapid-public-key").then((r) => r.data),
  subscribePush: (sub) => client.post("/push/subscribe", sub).then((r) => r.data),
  unsubscribePush: (endpoint) =>
    client.post("/push/unsubscribe", { endpoint }).then((r) => r.data),
  testPushBackend: () => client.post("/push/test").then((r) => r.data),
};
