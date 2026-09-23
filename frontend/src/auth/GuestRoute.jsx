import { Navigate } from "react-router-dom";

import { useAuth } from "./AuthContext";

export default function GuestRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="page-center">
        <div className="loader" aria-label="Loading" />
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
