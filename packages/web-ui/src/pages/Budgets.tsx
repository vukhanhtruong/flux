import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency } from "../lib/format";
import type { Budget } from "../types";

export function Budgets() {
  const { profile } = useProfile();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ category: "", monthly_limit: "" });

  async function fetchBudgets() {
    try {
      const data = await api.listBudgets(USER_ID);
      setBudgets(data);
    } catch (error) {
      console.error("Failed to fetch budgets:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchBudgets();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.setBudget({
        user_id: USER_ID,
        category: formData.category,
        monthly_limit: parseFloat(formData.monthly_limit),
      });
      setShowForm(false);
      setFormData({ category: "", monthly_limit: "" });
      await fetchBudgets();
    } catch (error) {
      console.error("Failed to set budget:", error);
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteBudget(id, USER_ID);
      await fetchBudgets();
    } catch (error) {
      console.error("Failed to delete budget:", error);
    }
  }

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Budgets</h1>
          <p className="mt-2 text-gray-600">Set and track budget limits for spending categories.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus size={18} />
          Set Budget
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-lg bg-white p-6 shadow">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Category</label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="e.g. Food, Transport"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Monthly Limit</label>
              <input
                type="number"
                step="0.01"
                value={formData.monthly_limit}
                onChange={(e) => setFormData({ ...formData, monthly_limit: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="0.00"
                required
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        </form>
      )}

      {budgets.length === 0 ? (
        <div className="rounded-lg bg-white p-8 text-center text-gray-500 shadow">
          No budgets set yet. Create your first budget!
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {budgets.map((budget) => (
            <div key={budget.id} className="rounded-lg bg-white p-6 shadow">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{budget.category}</h3>
                  <p className="mt-1 text-2xl font-bold text-gray-900">
                    {formatCurrency(budget.monthly_limit, profile.currency, profile.locale)}
                  </p>
                  <p className="text-sm text-gray-500">monthly limit</p>
                </div>
                <button
                  onClick={() => handleDelete(budget.id)}
                  className="text-red-500 hover:text-red-700"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <div className="mt-4">
                <div className="h-2 w-full rounded-full bg-gray-200">
                  <div className="h-2 rounded-full bg-green-500" style={{ width: "0%" }} />
                </div>
                <p className="mt-1 text-xs text-gray-500">Spending data available in Reports</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
