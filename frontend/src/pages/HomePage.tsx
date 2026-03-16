import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getContests,
  isApiError,
  login,
  registerParticipant,
} from "../api/client";
import type { Contest, User } from "../api/types";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { SubmissionsPanel } from "../features/submissions/SubmissionsPanel";

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
      <Panel
        title="Contests"
        subtitle="Published contests created by organizers will appear here."
      >
        <div className="empty-state">
          <h3>No contests yet</h3>
          <p>
            As soon as organizers publish contests, participants will see them
            here.
          </p>
        </div>
      </Panel>
    );
  }

  return (
    <Panel
      title="Available contests"
      subtitle="Open contest statements, submit solutions, and track standings."
    >
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
            ) : (
              <p className="contest-card__description contest-card__description--muted">
                No description provided.
              </p>
            )}

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
              <span>Status: {contest.status}</span>
              <span>Author: {contest.created_by.username}</span>
            </div>

            <div className="contest-card__footer">
              <Link
                to={`/contests/${contest.slug}`}
                className="button button--secondary"
              >
                Open contest
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

function AdminCommandCenter() {
  return (
    <Panel
      title="Admin command center"
      subtitle="Open the full organizer workspace for contest operations and judge monitoring."
    >
      <div className="action-card-grid">
        <Link to="/admin" className="action-card">
          <strong>Open admin workspace</strong>
          <span>
            Manage contests, problems, test cases, submissions, queue state, and
            rejudge operations.
          </span>
        </Link>

        <div className="action-card action-card--static">
          <strong>Recommended workflow</strong>
          <span>
            Create contest → add problems → configure test cases → publish →
            monitor queue and submissions.
          </span>
        </div>
      </div>
    </Panel>
  );
}

function AuthHero({
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
}) {
  return (
    <div className="landing-grid">
      <section className="hero-card">
        <div className="hero-card__eyebrow">Release candidate frontend</div>
        <h1 className="hero-card__title">
          Run programming contests in your local network with one clean interface.
        </h1>
        <p className="hero-card__lead">
          Organizers publish contests and problems, participants register,
          submit solutions, watch verdicts, and follow standings — all inside a
          single deployable system.
        </p>

        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-card__label">Judge model</span>
            <strong className="stat-card__value">Async + isolated</strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Languages</span>
            <strong className="stat-card__value">Python / C++</strong>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Deployment</span>
            <strong className="stat-card__value">Docker Compose</strong>
          </div>
        </div>
      </section>

      <Panel
        title={authMode === "login" ? "Sign in" : "Create participant account"}
        subtitle={
          authMode === "login"
            ? "Use your existing account to enter the system."
            : "Participants can self-register and immediately see published content."
        }
        className="auth-panel"
      >
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

        {feedbackMessage && feedbackType ? (
          <p className={`feedback feedback--${feedbackType}`}>
            {feedbackMessage}
          </p>
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
              <span>Full name (optional)</span>
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
              <span>Email (optional)</span>
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
              {busy ? "Creating account..." : "Create account"}
            </button>
          </form>
        )}
      </Panel>
    </div>
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

  const contestStats = useMemo(() => {
    const running = contests.filter((contest) => contest.phase === "running").length;
    const upcoming = contests.filter(
      (contest) => contest.phase === "upcoming",
    ).length;
    const finished = contests.filter(
      (contest) => contest.phase === "finished",
    ).length;

    return {
      total: contests.length,
      running,
      upcoming,
      finished,
    };
  }, [contests]);

  async function handleLoginSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthFeedbackMessage(null);
    setAuthFeedbackType(null);

    try {
      await login(loginState.username, loginState.password);
      await onAuthenticated();
      setLoginState(initialLoginState);
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
      setAuthFeedbackMessage(
        "Account created successfully. You can sign in now.",
      );
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
      <Panel title="Loading" subtitle="Checking your session.">
        <p className="muted">Please wait...</p>
      </Panel>
    );
  }

  if (!user) {
    return (
      <AuthHero
        authMode={authMode}
        onSwitchMode={setAuthMode}
        loginState={loginState}
        registerState={registerState}
        setLoginState={setLoginState}
        setRegisterState={setRegisterState}
        onLoginSubmit={handleLoginSubmit}
        onRegisterSubmit={handleRegisterSubmit}
        busy={authBusy}
        feedbackMessage={authFeedbackMessage}
        feedbackType={authFeedbackType}
      />
    );
  }

  return (
    <div className="dashboard-stack">
      <section className="page-head">
        <div>
          <span className="page-head__eyebrow">
            {user.role === "admin" ? "Admin dashboard" : "Participant dashboard"}
          </span>
          <h1 className="page-head__title">
            Welcome back, {user.full_name || user.username}
          </h1>
          <p className="page-head__subtitle">
            {user.role === "admin"
              ? "Manage contests, monitor judging, and coordinate the whole event from one place."
              : "Browse contests, solve problems, and track the state of your submissions."}
          </p>
        </div>
      </section>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-card__label">Published contests</span>
          <strong className="stat-card__value">{contestStats.total}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Running now</span>
          <strong className="stat-card__value">{contestStats.running}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Upcoming</span>
          <strong className="stat-card__value">{contestStats.upcoming}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Finished</span>
          <strong className="stat-card__value">{contestStats.finished}</strong>
        </div>
      </div>

      {contestError ? (
        <p className="feedback feedback--error">{contestError}</p>
      ) : null}

      {user.role === "admin" ? (
        <div className="dashboard-grid">
          <div className="dashboard-grid__main">
            <AdminCommandCenter />
            {contestsLoading ? (
              <Panel title="Available contests">
                <p className="muted">Loading contests...</p>
              </Panel>
            ) : (
              <ContestOverview contests={contests} />
            )}
          </div>

          <aside className="dashboard-grid__side">
            <SubmissionsPanel />
          </aside>
        </div>
      ) : (
        <div className="dashboard-grid">
          <div className="dashboard-grid__main">
            {contestsLoading ? (
              <Panel title="Available contests">
                <p className="muted">Loading contests...</p>
              </Panel>
            ) : (
              <ContestOverview contests={contests} />
            )}
          </div>

          <aside className="dashboard-grid__side">
            <SubmissionsPanel />
          </aside>
        </div>
      )}
    </div>
  );
}