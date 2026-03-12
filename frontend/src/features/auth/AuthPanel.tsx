import { useState } from "react";
import { isApiError, login, registerParticipant } from "../../api/client";
import { Panel } from "../../components/Panel";

interface AuthPanelProps {
  onAuthenticated: () => Promise<void>;
}

export function AuthPanel({ onAuthenticated }: AuthPanelProps) {
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [registerUsername, setRegisterUsername] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerFullName, setRegisterFullName] = useState("");
  const [busyAction, setBusyAction] = useState<"login" | "register" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyAction("login");
    setMessage(null);

    try {
      await login(loginUsername, loginPassword);
      await onAuthenticated();
    } catch (error) {
      setMessage(isApiError(error) ? error.message : "Login failed.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyAction("register");
    setMessage(null);

    try {
      await registerParticipant({
        username: registerUsername,
        password: registerPassword,
        email: registerEmail || undefined,
        full_name: registerFullName || undefined,
      });
      await login(registerUsername, registerPassword);
      await onAuthenticated();
    } catch (error) {
      setMessage(isApiError(error) ? error.message : "Registration failed.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="two-column-grid">
      <Panel title="Login">
        <form className="form-stack" onSubmit={handleLogin}>
          <label className="field">
            <span>Username</span>
            <input
              value={loginUsername}
              onChange={(event) => setLoginUsername(event.target.value)}
              placeholder="participant1"
              autoComplete="username"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={loginPassword}
              onChange={(event) => setLoginPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          <button type="submit" className="button" disabled={busyAction !== null}>
            {busyAction === "login" ? "Logging in..." : "Log in"}
          </button>
        </form>
      </Panel>

      <Panel title="Participant registration">
        <form className="form-stack" onSubmit={handleRegister}>
          <label className="field">
            <span>Username</span>
            <input
              value={registerUsername}
              onChange={(event) => setRegisterUsername(event.target.value)}
              placeholder="new-user"
              autoComplete="username"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={registerPassword}
              onChange={(event) => setRegisterPassword(event.target.value)}
              autoComplete="new-password"
            />
          </label>

          <label className="field">
            <span>Email</span>
            <input
              value={registerEmail}
              onChange={(event) => setRegisterEmail(event.target.value)}
              placeholder="user@example.com"
              autoComplete="email"
            />
          </label>

          <label className="field">
            <span>Full name</span>
            <input
              value={registerFullName}
              onChange={(event) => setRegisterFullName(event.target.value)}
              placeholder="Optional"
              autoComplete="name"
            />
          </label>

          <button type="submit" className="button" disabled={busyAction !== null}>
            {busyAction === "register" ? "Registering..." : "Register and log in"}
          </button>
        </form>
      </Panel>

      {message ? <p className="feedback feedback--error">{message}</p> : null}
    </div>
  );
}