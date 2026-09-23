import { Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function Dashboard() {
  const { user } = useAuth();

  if (user?.role === "instructor") {
    return <Navigate to="/instructor" replace />;
  }

  if (user?.role === "student") {
    return <Navigate to="/student" replace />;
  }

  return (
    <section className="panel">
      <h1>Unsupported account role</h1>
      <p className="muted">This account does not have a recognized portal role.</p>
    </section>
  );
}
