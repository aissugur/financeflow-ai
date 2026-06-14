import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Sidebar from "./components/Sidebar";
import { ErrorState } from "./components/ui/States";
import Overview from "./components/views/Overview";
import Ask from "./components/views/Ask";
import Evaluation from "./components/views/Evaluation";

const HEADINGS = {
  overview: { title: "Overview", sub: "Upload documents, then ask grounded questions." },
  ask: { title: "Ask", sub: "Questions are answered only from retrieved evidence." },
  evaluation: { title: "Evaluation", sub: "How well the assistant stays grounded." },
};

export default function App() {
  const [view, setView] = useState("overview");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [online, setOnline] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [demoSignal, setDemoSignal] = useState(0);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await api.listDocuments());
      setOnline(true);
    } catch (_) {
      setDocuments([]);
      setOnline(false);
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
      .catch(() => setOnline(false));
  }, [reload]);

  // "Try Demo": seed the sample documents, jump to Ask, auto-run a showcase Q.
  async function onTryDemo() {
    setSeeding(true);
    try {
      await api.seedDemo();
      await reload();
      setView("ask");
      setDemoSignal((n) => n + 1);
    } catch (_) {
      setOnline(false);
    } finally {
      setSeeding(false);
    }
  }

  const head = HEADINGS[view];

  return (
    <div className="app-shell">
      <Sidebar view={view} setView={setView} online={online} mode={health?.answer_mode} />

      <main className="main">
        <div className="view-head">
          <h1>{head.title}</h1>
          <p>{head.sub}</p>
        </div>

        {!online && (
          <div style={{ marginBottom: 20 }}>
            <ErrorState>
              Can’t reach the API. Start the backend with{" "}
              <code>uvicorn app.main:app --port 8000</code> and refresh.
            </ErrorState>
          </div>
        )}

        {view === "overview" && (
          <Overview
            documents={documents}
            loading={loading}
            reload={reload}
            onTryDemo={onTryDemo}
            seeding={seeding}
          />
        )}
        {view === "ask" && (
          <Ask
            documents={documents}
            demoSignal={demoSignal}
            onDemoConsumed={() => {}}
          />
        )}
        {view === "evaluation" && <Evaluation />}
      </main>
    </div>
  );
}
