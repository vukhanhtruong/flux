import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Transactions } from "./pages/Transactions";
import { Budgets } from "./pages/Budgets";
import { Goals } from "./pages/Goals";
import { Subscriptions } from "./pages/Subscriptions";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { ProfileProvider } from "./context/ProfileContext";

function App() {
  return (
    <BrowserRouter>
      <ProfileProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="budgets" element={<Budgets />} />
            <Route path="goals" element={<Goals />} />
            <Route path="subscriptions" element={<Subscriptions />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </ProfileProvider>
    </BrowserRouter>
  );
}

export default App;
