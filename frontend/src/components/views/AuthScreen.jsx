import { useEffect, useRef, useState } from "react";
import {
  IconCheck,
  IconEye,
  IconEyeOff,
  IconQuote,
  IconShield,
  IconSpark,
} from "../../lib/icons";
import Button from "../ui/Button";
import { ErrorState } from "../ui/States";

const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Renders the official Google Identity Services button when a client id is set;
// on success it hands the Google ID token to onCredential. Hidden otherwise.
function GoogleButton({ clientId, onCredential }) {
  const ref = useRef(null);
  const cbRef = useRef(onCredential);
  cbRef.current = onCredential;

  useEffect(() => {
    if (!clientId) return undefined;
    let cancelled = false;
    function render() {
      const gid = window.google?.accounts?.id;
      if (cancelled || !gid || !ref.current) return;
      gid.initialize({
        client_id: clientId,
        callback: (resp) => cbRef.current?.(resp.credential),
      });
      ref.current.innerHTML = "";
      gid.renderButton(ref.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        width: 320,
      });
    }
    if (window.google?.accounts?.id) {
      render();
      return () => {
        cancelled = true;
      };
    }
    let script = document.getElementById("gis-script");
    if (!script) {
      script = document.createElement("script");
      script.id = "gis-script";
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      document.body.appendChild(script);
    }
    script.addEventListener("load", render);
    return () => {
      cancelled = true;
      script.removeEventListener("load", render);
    };
  }, [clientId]);

  if (!clientId) return null;
  return <div className="auth-google" ref={ref} />;
}

export default function AuthScreen({
  onSignIn,
  onSignUp,
  onGoogle,
  onDemo,
  googleClientId,
  loading = false,
  serverError = "",
}) {
  const [mode, setMode] = useState("signin"); // 'signin' | 'signup'
  const [show, setShow] = useState(false);
  const [values, setValues] = useState({ email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const isSignup = mode === "signup";

  function validate(v = values) {
    const e = {};
    if (!v.email) e.email = "Email is required.";
    else if (!emailRe.test(v.email)) e.email = "Enter a valid email address.";
    if (!v.password) e.password = "Password is required.";
    else if (isSignup && v.password.length < 8) e.password = "Use at least 8 characters.";
    if (isSignup && v.confirm !== v.password) e.confirm = "Passwords don’t match.";
    return e;
  }

  function setField(name, val) {
    const next = { ...values, [name]: val };
    setValues(next);
    if (touched[name]) setErrors(validate(next));
  }

  function switchMode(next) {
    setMode(next);
    setErrors({});
    setTouched({});
  }

  async function onSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    setTouched({ email: true, password: true, confirm: true });
    if (Object.keys(e).length) return;
    const payload = { email: values.email.trim(), password: values.password };
    if (isSignup) await onSignUp?.(payload);
    else await onSignIn?.(payload);
  }

  const eid = (n) => `auth-${n}`;
  const errId = (n) => (errors[n] ? `${eid(n)}-err` : undefined);

  return (
    <div className="auth">
      {/* ---- Brand / feature panel ---- */}
      <aside className="auth-brand">
        <div className="auth-brand-top">
          <span className="brand-mark">
            <IconSpark size={16} />
          </span>
          <span className="auth-brand-name">
            FinanceFlow <span>AI</span>
          </span>
        </div>
        <div className="auth-brand-body">
          <h1 className="auth-brand-h1">
            Answers you can <span className="clip-light">prove.</span>
          </h1>
          <p className="auth-brand-sub">
            Source-grounded document Q&amp;A — every answer cites the exact line, and
            it abstains when the evidence isn’t there.
          </p>
          <ul className="auth-feat">
            <li>
              <IconQuote size={18} />
              <div>
                <b>Citation-first</b>
                <span>Every claim shows its source excerpt and page.</span>
              </div>
            </li>
            <li>
              <IconShield size={18} />
              <div>
                <b>Abstains when unsure</b>
                <span>Replies “Not enough information” instead of guessing.</span>
              </div>
            </li>
            <li>
              <IconCheck size={18} />
              <div>
                <b>Graded on every run</b>
                <span>A golden-dataset evaluation scores its grounding.</span>
              </div>
            </li>
          </ul>
        </div>
        <p className="auth-brand-foot">Source-backed document intelligence.</p>
      </aside>

      {/* ---- Form panel ---- */}
      <main className="auth-form-col">
        <div className="auth-card">
          <div className="segmented auth-toggle" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              role="tab"
              aria-selected={!isSignup}
              className={`seg ${!isSignup ? "active" : ""}`}
              onClick={() => switchMode("signin")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={isSignup}
              className={`seg ${isSignup ? "active" : ""}`}
              onClick={() => switchMode("signup")}
            >
              Sign up
            </button>
          </div>

          <div className="auth-head">
            <h2>{isSignup ? "Create your account" : "Welcome back"}</h2>
            <p>
              {isSignup
                ? "Start asking questions grounded in your own documents."
                : "Sign in to continue to your workspace."}
            </p>
          </div>

          {serverError && (
            <div style={{ marginBottom: 16 }}>
              <ErrorState>{serverError}</ErrorState>
            </div>
          )}

          <form className="auth-fields" onSubmit={onSubmit} noValidate>
            <label className="field" htmlFor={eid("email")}>
              <span className="field-label">Email</span>
              <input
                id={eid("email")}
                className="input"
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={values.email}
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errId("email")}
                onBlur={() => {
                  setTouched((t) => ({ ...t, email: true }));
                  setErrors(validate());
                }}
                onChange={(e) => setField("email", e.target.value)}
              />
              {errors.email && (
                <span className="field-error" id={errId("email")} role="alert">
                  {errors.email}
                </span>
              )}
            </label>

            <label className="field" htmlFor={eid("password")}>
              <span className="field-label">Password</span>
              <span className="auth-input-wrap">
                <input
                  id={eid("password")}
                  className="input"
                  type={show ? "text" : "password"}
                  autoComplete={isSignup ? "new-password" : "current-password"}
                  placeholder="••••••••"
                  value={values.password}
                  aria-invalid={errors.password ? true : undefined}
                  aria-describedby={errId("password")}
                  onBlur={() => {
                    setTouched((t) => ({ ...t, password: true }));
                    setErrors(validate());
                  }}
                  onChange={(e) => setField("password", e.target.value)}
                />
                <button
                  type="button"
                  className="auth-eye"
                  aria-pressed={show}
                  aria-label={show ? "Hide password" : "Show password"}
                  onClick={() => setShow((s) => !s)}
                >
                  {show ? <IconEyeOff size={18} /> : <IconEye size={18} />}
                </button>
              </span>
              {errors.password && (
                <span className="field-error" id={errId("password")} role="alert">
                  {errors.password}
                </span>
              )}
            </label>

            {isSignup && (
              <label className="field" htmlFor={eid("confirm")}>
                <span className="field-label">Confirm password</span>
                <input
                  id={eid("confirm")}
                  className="input"
                  type={show ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  value={values.confirm}
                  aria-invalid={errors.confirm ? true : undefined}
                  aria-describedby={errId("confirm")}
                  onBlur={() => {
                    setTouched((t) => ({ ...t, confirm: true }));
                    setErrors(validate());
                  }}
                  onChange={(e) => setField("confirm", e.target.value)}
                />
                {errors.confirm && (
                  <span className="field-error" id={errId("confirm")} role="alert">
                    {errors.confirm}
                  </span>
                )}
              </label>
            )}

            <Button type="submit" variant="primary" size="lg" block loading={loading}>
              {isSignup ? "Create account" : "Sign in"}
            </Button>
          </form>

          <GoogleButton clientId={googleClientId} onCredential={onGoogle} />

          <div className="auth-divider">
            <span>or</span>
          </div>
          <button
            type="button"
            className="auth-demo-link"
            onClick={onDemo}
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? "Starting demo…" : "Continue with the demo →"}
          </button>

          <p className="auth-switch">
            {isSignup ? "Already have an account? " : "New to FinanceFlow? "}
            <button type="button" onClick={() => switchMode(isSignup ? "signin" : "signup")}>
              {isSignup ? "Sign in" : "Create one"}
            </button>
          </p>
        </div>
      </main>
    </div>
  );
}
