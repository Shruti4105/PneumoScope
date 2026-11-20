import { lazy, Suspense, type ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Loading } from "./components/ui";
import { useAuth } from "./context/AuthContext";
import AppLayout from "./layouts/AppLayout";

const Home = lazy(() => import("./pages/HomePage"));
const Login = lazy(() => import("./pages/LoginPage"));
const Dashboard = lazy(() => import("./pages/DashboardPage"));
const Analyse = lazy(() => import("./pages/AnalysePage"));
const History = lazy(() => import("./pages/HistoryPage"));
const Result = lazy(() => import("./pages/ResultPage"));
const Performance = lazy(() => import("./pages/PerformancePage"));
const About = lazy(() => import("./pages/AboutPage"));

/** Pages inside the app require a signed-in user. */
function RequireLogin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Loading className="min-h-screen" />;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <>{children}</>;
}

const page = (el: ReactNode) => <Suspense fallback={<Loading />}>{el}</Suspense>;

export default function App() {
  return (
    <Routes>
      <Route path="/" element={page(<Home />)} />
      <Route path="/login" element={page(<Login />)} />
      <Route element={<RequireLogin><AppLayout /></RequireLogin>}>
        <Route path="/dashboard" element={page(<Dashboard />)} />
        <Route path="/analyse" element={page(<Analyse />)} />
        <Route path="/history" element={page(<History />)} />
        <Route path="/history/:id" element={page(<Result />)} />
        <Route path="/performance" element={page(<Performance />)} />
        <Route path="/about" element={page(<About />)} />
      </Route>
      <Route path="*" element={
        <div className="py-24 text-center">
          <h1 className="text-xl font-semibold">Page not found</h1>
          <Link to="/" className="btn-secondary mt-4">Back to home</Link>
        </div>
      } />
    </Routes>
  );
}
