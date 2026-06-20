import { useCallback, useEffect, useState } from "react";
import { api, setOnUnauthorized, tokenStore } from "./api";
import { IconSpark } from "./lib/icons";
import Sidebar from "./components/Sidebar";
import Button from "./components/ui/Button";
import { ErrorState } from "./components/ui/States";
import Overview from "./components/views/Overview";
import Ask from "./components/views/Ask";
import Evaluation from "./components/views/Evaluation";
import AuthScreen from "./components/views/AuthScreen";

const HEADINGS = {
  ask: { title: "Ask", sub: "Questions are answered only from retrieved evidence." },
  evaluation: { title: "Evaluation", sub: "How well the assistant stays grounded." },
};

function randHex(bytes) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

export default function App() {
  const [view, setView] = useState("overview");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [online, setOnline] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [demoSignal, setDemoSignal] = useState(0);
  const [scrolled, setScrolled] = useState(false);

  // ---- Auth state ----
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Mount: load public health (so the auth screen knows if Google is enabled) and
  // validate any stored token. A 401 later surfaces a friendly expiry message.
  useEffect(() => {
    setOnUnauthorized((msg) => {
      setAuthError(msg || "");
      setUser(null);
    });
    api
      .health()
      .then((h) => {
        setHealth(h);
        setOnline(true);
      })
      .catch(() => setOnline(false));
    if (!tokenStore.get()) {
      setAuthReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => {})
      .finally(() => setAuthReady(true));
  }, []);

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

  // Load documents once authenticated.
  useEffect(() => {
    if (!user) return;
    reload();
  }, [reload, user]);

  async function handleAuth(fn, creds) {
    setAuthError("");
    setAuthBusy(true);
    try {
      const res = await fn(creds);
      setUser(res.user);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthBusy(false);
    }
  }

  function handleGoogle(credential) {
    return handleAuth(() => api.googleLogin(credential));
  }

  // Guest path: a throwaway account with CSPRNG creds (no predictable secrets).
  async function continueAsGuest() {
    const res = await api.register({
      email: `guest_${randHex(8)}@financeflow-guest.com`,
      password: randHex(24),
    });
    setUser(res.user);
  }

  async function onDemo() {
    setAuthError("");
    setAuthBusy(true);
    try {
      await continueAsGuest();
      await onTryDemo();
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthBusy(false);
    }
  }

  function onLogout() {
    api.logout();
    setUser(null);
    setDocuments([]);
    setView("overview");
  }

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

  // ---- Gate: validating -> nothing; logged out -> auth screen ----
  if (!authReady) return null;
  if (!user) {
    return (
      <AuthScreen
        loading={authBusy}
        serverError={authError}
        googleClientId={health?.google_client_id}
        onSignIn={(c) => handleAuth(api.login, c)}
        onSignUp={(c) => handleAuth(api.register, c)}
        onGoogle={handleGoogle}
        onDemo={onDemo}
      />
    );
  }

  const head = HEADINGS[view];

  return (
    <div className="app-shell">
      <Sidebar
        view={view}
        setView={setView}
        online={online}
        llmAvailable={health?.llm_available}
        userEmail={user.email}
        onLogout={onLogout}
      />

      <main className="main">
        <div className={`topbar ${scrolled ? "show" : ""}`}>
          <span className="topbar-brand">
            <span
              style={{
                width: 22, height: 22, borderRadius: 7,
                background: "var(--accent-grad)", display: "inline-grid", placeItems: "center",
              }}
            >
              <IconSpark size={13} />
            </span>
            FinanceFlow AI
          </span>
          <nav className="topbar-nav">
            <button type="button" onClick={() => setView("overview")}>Overview</button>
            <button type="button" onClick={() => setView("ask")}>Ask</button>
            <button type="button" onClick={() => setView("evaluation")}>Evaluation</button>
          </nav>
          <Button variant="primary" size="sm" loading={seeding} onClick={onTryDemo}>
            Try demo
          </Button>
        </div>

        {view !== "overview" && (
          <div className="view-head">
            <h1>{head.title}</h1>
            <p>{head.sub}</p>
          </div>
        )}

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
            onOpenEval={() => setView("evaluation")}
          />
        )}
        {view === "ask" && (
          <Ask
            documents={documents}
            demoSignal={demoSignal}
            llmAvailable={health?.llm_available}
            onDemoConsumed={() => {}}
          />
        )}
        {view === "evaluation" && <Evaluation />}
      </main>
    </div>
  );
}
