import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import AskPanel from "./components/AskPanel";
import Dashboard from "./components/Dashboard";
import Evaluation from "./components/Evaluation";

const TABS = ["Dashboard", "Ask", "Evaluation"];

export default function App() {
  const [tab, setTab] = useState("Dashboard");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [online, setOnline] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await api.listDocuments());
    } catch (_) {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
    api
      .health()
      .then((h) => {
        setHealth(h);
        setOnline(true);
      })
      .catch(() => {
        setHealth(null);
        setOnline(false);
      });
  }, [reload]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span> FinanceFlow <span className="ai">AI</span>
        </div>
        <div className="tagline">
          Ask your finance documents. Get source-backed answers.
        </div>
        {health && (
          <div className="health">
            mode: <strong>{health.answer_mode}</strong>
          </div>
        )}
      </header>

      {!online && (
        <div className="banner-offline">
          ⚠️ Can't reach the backend API. Start it with{" "}
          <code>uvicorn app.main:app --port 8000</code> in the <code>backend</code>{" "}
          folder, then refresh.
        </div>
      )}

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={tab === t ? "tab active" : "tab"}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>

      <main className="content">
        {tab === "Dashboard" && (
          <Dashboard documents={documents} reload={reload} loading={loading} />
        )}
        {tab === "Ask" && <AskPanel documents={documents} />}
        {tab === "Evaluation" && <Evaluation />}
      </main>

      <footer className="footer">
        FinanceFlow AI — MVP demo. Answers are grounded in your uploaded
        documents only.
      </footer>
    </div>
  );
}
