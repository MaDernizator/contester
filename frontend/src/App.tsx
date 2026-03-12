import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { getCurrentUser, isApiError, logout } from "./api/client";
import type { User } from "./api/types";
import { PageShell } from "./components/PageShell";
import { ContestPage } from "./pages/ContestPage";
import { HomePage } from "./pages/HomePage";
import { ProblemPage } from "./pages/ProblemPage";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);

  async function refreshSession() {
    setSessionLoading(true);

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      if (isApiError(error) && error.status === 401) {
        setUser(null);
      } else {
        console.error(error);
        setUser(null);
      }
    } finally {
      setSessionLoading(false);
    }
  }

  useEffect(() => {
    void refreshSession();
  }, []);

  async function handleLogout() {
    try {
      await logout();
    } catch (error) {
      console.error(error);
    } finally {
      setUser(null);
    }
  }

  return (
    <BrowserRouter>
      <PageShell user={user} onLogout={handleLogout}>
        <Routes>
          <Route
            path="/"
            element={
              <HomePage
                user={user}
                sessionLoading={sessionLoading}
                onAuthenticated={refreshSession}
              />
            }
          />
          <Route path="/contests/:contestSlug" element={<ContestPage user={user} />} />
          <Route
            path="/contests/:contestSlug/problems/:problemCode"
            element={<ProblemPage user={user} />}
          />
        </Routes>
      </PageShell>
    </BrowserRouter>
  );
}