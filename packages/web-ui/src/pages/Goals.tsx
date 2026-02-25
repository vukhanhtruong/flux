import { useEffect, useState } from "react";
import { Plus, Trash2, ArrowUpCircle, ArrowDownCircle } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Goal } from "../types";

export function Goals() {
  const { profile } = useProfile();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [depositGoalId, setDepositGoalId] = useState<string | null>(null);
  const [depositAmount, setDepositAmount] = useState("");
  const [formData, setFormData] = useState({ name: "", target_amount: "", deadline: "" });

  async function fetchGoals() {
    try {
      const data = await api.listGoals(USER_ID);
      setGoals(data);
    } catch (error) {
      console.error("Failed to fetch goals:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchGoals();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.createGoal({
        user_id: USER_ID,
        name: formData.name,
        target_amount: parseFloat(formData.target_amount),
        deadline: formData.deadline || new Date().toISOString().split("T")[0],
      });
      setShowForm(false);
      setFormData({ name: "", target_amount: "", deadline: "" });
      await fetchGoals();
    } catch (error) {
      console.error("Failed to create goal:", error);
    }
  }

  async function handleDeposit(goal: Goal, isWithdraw: boolean) {
    const amount = parseFloat(depositAmount);
    if (!amount || amount <= 0) return;
    const currentAmount = parseFloat(goal.current_amount);
    const newAmount = isWithdraw
      ? Math.max(0, currentAmount - amount)
      : currentAmount + amount;
    try {
      await api.updateGoal(goal.id, USER_ID, { current_amount: newAmount });
      setDepositGoalId(null);
      setDepositAmount("");
      await fetchGoals();
    } catch (error) {
      console.error("Failed to update goal:", error);
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteGoal(id, USER_ID);
      await fetchGoals();
    } catch (error) {
      console.error("Failed to delete goal:", error);
    }
  }

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Goals</h1>
          <p className="mt-2 text-gray-600">Track progress toward your financial goals.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus size={18} />
          Create Goal
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-lg bg-white p-6 shadow">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="e.g. Emergency Fund"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Target Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.target_amount}
                onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="0.00"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Deadline</label>
              <input
                type="date"
                value={formData.deadline}
                onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
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

      {goals.length === 0 ? (
        <div className="rounded-lg bg-white p-8 text-center text-gray-500 shadow">
          No goals yet. Set your first savings goal!
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal) => {
            const current = parseFloat(goal.current_amount);
            const target = parseFloat(goal.target_amount);
            const pct = target > 0 ? Math.min(100, (current / target) * 100) : 0;

            return (
              <div key={goal.id} className="rounded-lg bg-white p-6 shadow">
                <div className="flex items-start justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">{goal.name}</h3>
                  <button
                    onClick={() => handleDelete(goal.id)}
                    className="text-red-500 hover:text-red-700"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <div className="mt-3">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>{formatCurrency(current, profile.currency, profile.locale)}</span>
                    <span>{formatCurrency(target, profile.currency, profile.locale)}</span>
                  </div>
                  <div className="mt-1 h-3 w-full rounded-full bg-gray-200">
                    <div
                      className="h-3 rounded-full bg-green-500 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="mt-1 text-sm font-medium text-gray-700">{pct.toFixed(1)}%</p>
                </div>

                {goal.deadline && (
                  <p className="mt-2 text-xs text-gray-500">
                    Deadline: {formatDate(goal.deadline, profile.locale, profile.timezone)}
                  </p>
                )}

                <div className="mt-4">
                  {depositGoalId === goal.id ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        step="0.01"
                        value={depositAmount}
                        onChange={(e) => setDepositAmount(e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                        placeholder="Amount"
                      />
                      <button
                        onClick={() => handleDeposit(goal, false)}
                        className="rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700"
                        title="Deposit"
                      >
                        <ArrowUpCircle size={16} />
                      </button>
                      <button
                        onClick={() => handleDeposit(goal, true)}
                        className="rounded bg-orange-600 px-2 py-1 text-xs text-white hover:bg-orange-700"
                        title="Withdraw"
                      >
                        <ArrowDownCircle size={16} />
                      </button>
                      <button
                        onClick={() => { setDepositGoalId(null); setDepositAmount(""); }}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDepositGoalId(goal.id)}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Deposit / Withdraw
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
