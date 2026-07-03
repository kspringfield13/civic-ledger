import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import CaseQueue from "./pages/CaseQueue";
import Dashboard from "./pages/Dashboard";
import Entities from "./pages/Entities";
import RiskSignals from "./pages/RiskSignals";
import Sources from "./pages/Sources";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<Dashboard />} />
          <Route path="sources" element={<Sources />} />
          <Route path="entities" element={<Entities />} />
          <Route path="risk-signals" element={<RiskSignals />} />
          <Route path="cases" element={<CaseQueue />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
