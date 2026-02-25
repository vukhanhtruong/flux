import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Transaction, FinancialHealth } from "../types";

export function Dashboard() {
  const { profile } = useProfile();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [health, setHealth] = useState<FinancialHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [txns, healthData] = await Promise.all([
          api.listTransactions(USER_ID, 5),
          api.getFinancialHealth(
            USER_ID,
            new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
            new Date().toISOString().split("T")[0]
          ),
        ]);
        setTransactions(txns);
        setHealth(healthData);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Overview of your financial health and recent activity
        </p>
      </div>

      {health && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-sm font-medium text-gray-500">Health Score</h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">{health.score}/100</p>
          </div>
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-sm font-medium text-gray-500">Savings Rate</h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">
              {(health.savings_rate * 100).toFixed(1)}%
            </p>
          </div>
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-sm font-medium text-gray-500">Budget Adherence</h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">
              {(health.budget_adherence * 100).toFixed(1)}%
            </p>
          </div>
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-sm font-medium text-gray-500">Goal Progress</h3>
            <p className="mt-2 text-3xl font-semibold text-gray-900">
              {(health.goal_progress * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      <div className="rounded-lg bg-white shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Transactions</h2>
        </div>
        <div className="px-6 py-4">
          {transactions.length === 0 ? (
            <p className="text-gray-500">No transactions yet</p>
          ) : (
            <ul className="divide-y divide-gray-200">
              {transactions.map((txn) => (
                <li key={txn.id} className="py-3">
                  <div className="flex justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{txn.description}</p>
                      <p className="text-sm text-gray-500">
                        {txn.category} • {formatDate(txn.date, profile.locale, profile.timezone)}
                      </p>
                    </div>
                    <div
                      className={`text-lg font-semibold ${
                        txn.type === "income" ? "text-green-600" : "text-red-600"
                      }`}
                    >
                      {txn.type === "income" ? "+" : "-"}
                      {formatCurrency(txn.amount, profile.currency, profile.locale)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
