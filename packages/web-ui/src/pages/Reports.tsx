import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { SpendingReport, FinancialHealth } from "../types";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#6366F1", "#14B8A6"];

export function Reports() {
  const [report, setReport] = useState<SpendingReport | null>(null);
  const [health, setHealth] = useState<FinancialHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const today = new Date().toISOString().split("T")[0];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  const [startDate, setStartDate] = useState(thirtyDaysAgo);
  const [endDate, setEndDate] = useState(today);

  async function fetchReports() {
    setLoading(true);
    setError(null);
    try {
      const [reportData, healthData] = await Promise.all([
        api.getSpendingReport(USER_ID, startDate, endDate),
        api.getFinancialHealth(USER_ID, startDate, endDate),
      ]);
      setReport(reportData);
      setHealth(healthData);
    } catch (err) {
      console.error("Failed to fetch reports:", err);
      setError("Failed to load reports. Make sure you have transactions in this date range.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchReports();
  }, [startDate, endDate]);

  const pieData = report
    ? Object.entries(report.category_breakdown).map(([name, value]) => ({
        name,
        value: parseFloat(value),
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
        <p className="mt-2 text-gray-600">View spending reports and financial health insights.</p>
      </div>

      <div className="flex items-center gap-4 rounded-lg bg-white p-4 shadow">
        <div>
          <label className="block text-sm font-medium text-gray-700">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="mt-1 rounded-md border border-gray-300 px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="mt-1 rounded-md border border-gray-300 px-3 py-2"
          />
        </div>
      </div>

      {loading && <div className="text-gray-600">Loading reports...</div>}
      {error && <div className="rounded-lg bg-red-50 p-4 text-red-700">{error}</div>}

      {!loading && !error && report && (
        <>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div className="rounded-lg bg-white p-6 shadow">
              <h3 className="text-sm font-medium text-gray-500">Total Income</h3>
              <p className="mt-2 text-3xl font-semibold text-green-600">
                ${parseFloat(report.total_income).toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow">
              <h3 className="text-sm font-medium text-gray-500">Total Expenses</h3>
              <p className="mt-2 text-3xl font-semibold text-red-600">
                ${parseFloat(report.total_expenses).toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow">
              <h3 className="text-sm font-medium text-gray-500">Net Savings</h3>
              <p
                className={`mt-2 text-3xl font-semibold ${
                  parseFloat(report.net_savings) >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                ${parseFloat(report.net_savings).toFixed(2)}
              </p>
            </div>
          </div>

          {pieData.length > 0 && (
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Spending by Category</h2>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={120}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  >
                    {pieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `$${Number(value).toFixed(2)}`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {health && (
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Financial Health</h2>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Health Score</h3>
                  <p className="mt-1 text-3xl font-bold text-gray-900">{health.score}/100</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Savings Rate</h3>
                  <p className="mt-1 text-3xl font-bold text-gray-900">
                    {(health.savings_rate * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Budget Adherence</h3>
                  <p className="mt-1 text-3xl font-bold text-gray-900">
                    {(health.budget_adherence * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Goal Progress</h3>
                  <p className="mt-1 text-3xl font-bold text-gray-900">
                    {(health.goal_progress * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
