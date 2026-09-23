import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="page-center">
      <section className="not-found">
        <div className="eyebrow">404</div>
        <h1>Page not found</h1>
        <p className="muted">The page you requested does not exist.</p>
        <Link className="button button-primary" to="/">
          Go home
        </Link>
      </section>
    </main>
  );
}
