import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Suspense, lazy } from "react";
import { Layout } from "./components/Layout";
import { ProfileProvider } from "./context/ProfileContext";
import { ErrorBoundary } from "./components/ErrorBoundary";

// Lazy-loaded route components
const Dashboard = lazy(() => import("./pages/Dashboard").then(m => ({ default: m.Dashboard })));
const Transactions = lazy(() => import("./pages/Transactions").then(m => ({ default: m.Transactions })));
const Budgets = lazy(() => import("./pages/Budgets").then(m => ({ default: m.Budgets })));
const Goals = lazy(() => import("./pages/Goals").then(m => ({ default: m.Goals })));
const Subscriptions = lazy(() => import("./pages/Subscriptions").then(m => ({ default: m.Subscriptions })));
const Assets = lazy(() => import("./pages/Assets").then(m => ({ default: m.Assets })));
const Reports = lazy(() => import("./pages/Reports").then(m => ({ default: m.Reports })));
const Settings = lazy(() => import("./pages/Settings").then(m => ({ default: m.Settings })));

// Global Loading fallback wrapper for lazy routes
const LoadingFallback = () => (
  <div className="flex items-center justify-center min-h-[400px]">
    <div className="flex flex-col items-center gap-4">
      <div className="w-8 h-8 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
      <span className="text-slate-400 text-sm font-medium animate-pulse">Loading interface...</span>
    </div>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <ProfileProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Dashboard />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="transactions" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Transactions />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="budgets" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Budgets />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="goals" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Goals />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="subscriptions" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Subscriptions />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="assets" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Assets />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="reports" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Reports />
                </Suspense>
              </ErrorBoundary>
            } />
            <Route path="settings" element={
              <ErrorBoundary>
                <Suspense fallback={<LoadingFallback />}>
                  <Settings />
                </Suspense>
              </ErrorBoundary>
            } />
          </Route>
        </Routes>
      </ProfileProvider>
    </BrowserRouter>
  );
}

export default App;
