import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getContests,
  isApiError,
  login,
  registerParticipant,
} from "../api/client";
import type { Contest, User } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { FormErrorList } from "../components/FormErrorList";
import { LoadingState } from "../components/LoadingState";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { SubmissionsPanel } from "../features/submissions/SubmissionsPanel";
import {
  validateLoginForm,
  validateRegisterForm,
} from "../features/validation/forms";

interface HomePageProps {
  user: User | null;
  sessionLoading: boolean;
  onAuthenticated: () => void | Promise<void>;
}

type AuthMode = "login" | "register";

interface LoginFormState {
  username: string;
  password: string;
}

interface RegisterFormState {
  username: string;
  password: string;
  email: string;
  full_name: string;
}

const initialLoginState: LoginFormState = {
  username: "",
  password: "",
};

const initialRegisterState: RegisterFormState = {
  username: "",
  password: "",
  email: "",
  full_name: "",
};

function ContestOverview({ contests }: { contests: Contest[] }) {
  if (contests.length === 0) {
    return (
      <Panel title="Contests">
        <EmptyState
          title="No contests yet"
          description="Published contests will appear here."
        />
      </Panel>
    );
  }

  return (
    <Panel title="Contests">
      <div className="contest-grid">
        {contests.map((contest) => (
          <article key={contest.id} className="contest-card">
            <div className="contest-card__header">
              <div>
                <h3 className="contest-card__title">{contest.title}</h3>
                <p className="contest-card__meta">{contest.slug}</p>
              </div>
              <StatusPill value={contest.phase} />
            </div>

            {contest.description ? (
              <p className="contest-card__description">{contest.description}</p>
            ) : null}

            <div className="meta-grid">
              <span>
                Starts:{" "}
                {contest.starts_at
                  ? new Date(contest.starts_at).toLocaleString()
                  : "—"}
              </span>
              <span>
                Ends:{" "}
                {contest.ends_at
                  ? new Date(contest.ends_at).toLocaleString()
                  : "—"}
              </span>
            </div>

            <div className="contest-card__footer">
              <Link
                to={`/contests/${contest.slug}`}
                className="button button--secondary"
              >
                Open
              </Link>
              <Link
                to={`/contests/${contest.slug}/standings`}
                className="inline-link"
              >
                Standings
              </Link>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}

function AuthCard({
  authMode,
  onSwitchMode,
  loginState,
  registerState,
  setLoginState,
  setRegisterState,
  onLoginSubmit,
  onRegisterSubmit,
  busy,
  feedbackMessage,
  feedbackType,
  validationErrors,
}: {
  authMode: AuthMode;
  onSwitchMode: (mode: AuthMode) => void;
  loginState: LoginFormState;
  registerState: RegisterFormState;
  setLoginState: React.Dispatch<React.SetStateAction<LoginFormState>>;
  setRegisterState: React.Dispatch<React.SetStateAction<RegisterFormState>>;
  onLoginSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onRegisterSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  busy: boolean;
  feedbackMessage: string | null;
  feedbackType: "success" | "error" | null;
  validationErrors: string[];
}) {
  return (
    <Panel title={authMode === "login" ? "Sign in" : "Register"}>
      <div className="auth-tabs">
        <button
          type="button"
          className={`auth-tab ${authMode === "login" ? "auth-tab--active" : ""}`}
          onClick={() => onSwitchMode("login")}
        >
          Login
        </button>
        <button
          type="button"
          className={`auth-tab ${authMode === "register" ? "auth-tab--active" : ""}`}
          onClick={() => onSwitchMode("register")}
        >
          Register
        </button>
      </div>

      <FormErrorList errors={validationErrors} />

      {feedbackMessage && feedbackType ? (
        <p className={`feedback feedback--${feedbackType}`}>{feedbackMessage}</p>
      ) : null}

      {authMode === "login" ? (
        <form className="form-stack" onSubmit={onLoginSubmit}>
          <label className="field">
            <span>Username</span>
            <input
              value={loginState.username}
              onChange={(event) =>
                setLoginState((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
              autoComplete="username"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={loginState.password}
              onChange={(event) =>
                setLoginState((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
              autoComplete="current-password"
            />
          </label>

          <button type="submit" className="button" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>
      ) : (
        <form className="form-stack" onSubmit={onRegisterSubmit}>
          <label className="field">
            <span>Username</span>
            <input
              value={registerState.username}
              onChange={(event) =>
                setRegisterState((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
              autoComplete="username"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={registerState.password}
              onChange={(event) =>
                setRegisterState((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
              autoComplete="new-password"
            />
          </label>

          <label className="field">
            <span>Full name</span>
            <input
              value={registerState.full_name}
              onChange={(event) =>
                setRegisterState((current) => ({
                  ...current,
                  full_name: event.target.value,
                }))
              }
              autoComplete="name"
            />
          </label>

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={registerState.email}
              onChange={(event) =>
                setRegisterState((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
              autoComplete="email"
            />
          </label>

          <button type="submit" className="button" disabled={busy}>
            {busy ? "Creating..." : "Create account"}
          </button>
        </form>
      )}
    </Panel>
  );
}

export function HomePage({
  user,
  sessionLoading,
  onAuthenticated,
}: HomePageProps) {
  const [contests, setContests] = useState<Contest[]>([]);
  const [contestsLoading, setContestsLoading] = useState(false);
  const [contestError, setContestError] = useState<string | null>(null);

  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [loginState, setLoginState] = useState(initialLoginState);
  const [registerState, setRegisterState] = useState(initialRegisterState);
  const [authBusy, setAuthBusy] = useState(false);
  const [authFeedbackMessage, setAuthFeedbackMessage] = useState<string | null>(
    null,
  );
  const [authFeedbackType, setAuthFeedbackType] = useState<
    "success" | "error" | null
  >(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    if (!user) {
      return;
    }

    void (async () => {
      setContestsLoading(true);
      setContestError(null);

      try {
        const data = await getContests();
        setContests(data);
      } catch (error) {
        setContestError(
          isApiError(error) ? error.message : "Failed to load contests.",
        );
      } finally {
        setContestsLoading(false);
      }
    })();
  }, [user]);

  const runningCount = useMemo(
    () => contests.filter((contest) => contest.phase === "running").length,
    [contests],
  );

  async function handleLoginSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthFeedbackMessage(null);
    setAuthFeedbackType(null);

    const errors = validateLoginForm(loginState);
    setValidationErrors(errors);

    if (errors.length > 0) {
      setAuthBusy(false);
      return;
    }

    try {
      await login(loginState.username, loginState.password);
      await onAuthenticated();
      setLoginState(initialLoginState);
      setValidationErrors([]);
    } catch (error) {
      setAuthFeedbackType("error");
      setAuthFeedbackMessage(
        isApiError(error) ? error.message : "Failed to sign in.",
      );
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleRegisterSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthFeedbackMessage(null);
    setAuthFeedbackType(null);

    const errors = validateRegisterForm(registerState);
    setValidationErrors(errors);

    if (errors.length > 0) {
      setAuthBusy(false);
      return;
    }

    try {
      await registerParticipant({
        username: registerState.username,
        password: registerState.password,
        email: registerState.email || undefined,
        full_name: registerState.full_name || undefined,
      });

      setRegisterState(initialRegisterState);
      setAuthMode("login");
      setAuthFeedbackType("success");
      setAuthFeedbackMessage("Account created. You can sign in now.");
      setValidationErrors([]);
    } catch (error) {
      setAuthFeedbackType("error");
      setAuthFeedbackMessage(
        isApiError(error) ? error.message : "Failed to create account.",
      );
    } finally {
      setAuthBusy(false);
    }
  }

  if (sessionLoading) {
    return (
      <Panel title="Loading">
        <LoadingState label="Checking your session..." />
      </Panel>
    );
  }

  if (!user) {
    return (
      <div className="home-auth-layout">
        <AuthCard
          authMode={authMode}
          onSwitchMode={(mode) => {
            setAuthMode(mode);
            setValidationErrors([]);
            setAuthFeedbackMessage(null);
            setAuthFeedbackType(null);
          }}
          loginState={loginState}
          registerState={registerState}
          setLoginState={setLoginState}
          setRegisterState={setRegisterState}
          onLoginSubmit={handleLoginSubmit}
          onRegisterSubmit={handleRegisterSubmit}
          busy={authBusy}
          feedbackMessage={authFeedbackMessage}
          feedbackType={authFeedbackType}
          validationErrors={validationErrors}
        />

        <Panel title="Contester">
          <div className="home-compact-info">
            <strong>Local contest system</strong>
            <span>Python and C++ submissions</span>
            <span>Asynchronous isolated judge</span>
            <span>Standings and admin workspace</span>
          </div>
        </Panel>
      </div>
    );
  }

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">
            {user.role === "admin" ? "Admin" : "Participant"}
          </span>
          <h1 className="page-head__title">
            {user.full_name || user.username}
          </h1>
          <p className="page-head__subtitle">
            {contests.length} contests · {runningCount} running
          </p>
        </div>

        {user.role === "admin" ? (
          <div className="page-actions">
            <Link to="/admin" className="button">
              Open admin workspace
            </Link>
          </div>
        ) : null}
      </section>

      {contestError ? <p className="feedback feedback--error">{contestError}</p> : null}

      <div className="dashboard-grid dashboard-grid--wide">
        <div className="dashboard-grid__main">
          {contestsLoading ? (
            <Panel title="Contests">
              <LoadingState label="Loading contests..." />
            </Panel>
          ) : (
            <ContestOverview contests={contests} />
          )}
        </div>

        <aside className="dashboard-grid__side">
          <SubmissionsPanel />
        </aside>
      </div>
    </div>
  );
}