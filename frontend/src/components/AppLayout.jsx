import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/dashboard" className="brand">
          <span className="brand-mark">EA</span>
          <span>
            <strong>EdTech Autograder</strong>
            <small>Python assessment portal</small>
          </span>
        </NavLink>

        <nav className="topbar-actions" aria-label="Main navigation">
          <span className="user-pill">
            <span className="user-pill-name">
              {user?.full_name || user?.email}
            </span>
            <span className="role-badge">{user?.role}</span>
          </span>
          <button className="button button-ghost" type="button" onClick={handleLogout}>
            Log out
          </button>
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
