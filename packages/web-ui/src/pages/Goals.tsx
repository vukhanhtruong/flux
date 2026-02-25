import { useEffect, useState } from "react";
import { Plus, Trash2, ArrowUpCircle, ArrowDownCircle, Target } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { Goal } from "../types";

export function Goals() {
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
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Financial Goals</h1>
          <p className="text-slate-400">Track progress toward your financial milestones.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          {showForm ? <Trash2 size={18} /> : <Plus size={18} />}
          {showForm ? "Cancel" : "Create Goal"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="glass-card p-8 animate-in slide-in-from-top duration-500">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Goal Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                placeholder="e.g. Dream House, New Car"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Target Amount</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">$</span>
                <input
                  type="number"
                  step="0.01"
                  value={formData.target_amount}
                  onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-8 pr-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                  placeholder="0.00"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Deadline</label>
              <input
                type="date"
                value={formData.deadline}
                onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
              />
            </div>
          </div>
          <div className="mt-8 flex justify-end">
            <button
              type="submit"
              className="btn-primary min-w-[120px]"
            >
              Save Goal
            </button>
          </div>
        </form>
      )}

      {goals.length === 0 ? (
        <div className="glass-card p-20 text-center">
          <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Target className="w-10 h-10 text-slate-500" />
          </div>
          <p className="text-slate-500 text-lg italic">No goals yet. Set your first savings goal!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal) => {
            const current = parseFloat(goal.current_amount);
            const target = parseFloat(goal.target_amount);
            const pct = target > 0 ? Math.min(100, (current / target) * 100) : 0;

            return (
              <div key={goal.id} className="glass-card p-8 flex flex-col h-full hover:border-white/20 transition-all group">
                <div className="flex items-start justify-between mb-6">
                  <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">{goal.name}</h3>
                  <button
                    onClick={() => handleDelete(goal.id)}
                    className="p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                    title="Delete"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>

                <div className="flex-1 space-y-4">
                  <div className="flex justify-between items-end pb-1">
                    <span className="text-2xl font-bold text-white">${current.toLocaleString()}</span>
                    <span className="text-sm text-slate-500">of ${target.toLocaleString()}</span>
                  </div>

                  <div className="h-4 w-full rounded-full bg-white/5 overflow-hidden border border-white/5 p-0.5">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${pct >= 100 ? 'bg-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.5)]' : 'bg-primary shadow-[0_0_15px_rgba(245,158,11,0.5)]'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-xs font-bold uppercase tracking-widest text-slate-500 italic">
                    <span>{pct.toFixed(1)}% Completed</span>
                    {goal.deadline && (
                      <span className="text-slate-400">Due {new Date(goal.deadline).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-6 border-t border-white/5">
                  {depositGoalId === goal.id ? (
                    <div className="flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
                      <div className="relative flex-1">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs">$</span>
                        <input
                          type="number"
                          step="0.01"
                          value={depositAmount}
                          onChange={(e) => setDepositAmount(e.target.value)}
                          className="w-full bg-white/5 border border-white/10 rounded-xl pl-6 pr-2 py-2 text-sm text-white outline-none focus:border-primary/50 transition-colors"
                          placeholder="0.00"
                          autoFocus
                        />
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleDeposit(goal, false)}
                          className="p-2 rounded-lg bg-emerald-400 hover:bg-emerald-500 text-dark transition-colors"
                          title="Deposit"
                        >
                          <ArrowUpCircle size={18} />
                        </button>
                        <button
                          onClick={() => handleDeposit(goal, true)}
                          className="p-2 rounded-lg bg-orange-400 hover:bg-orange-500 text-dark transition-colors"
                          title="Withdraw"
                        >
                          <ArrowDownCircle size={18} />
                        </button>
                        <button
                          onClick={() => { setDepositGoalId(null); setDepositAmount(""); }}
                          className="p-2 rounded-lg text-slate-400 hover:text-white transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDepositGoalId(goal.id)}
                      className="w-full py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm font-semibold text-white hover:bg-white/10 hover:border-white/20 transition-all flex items-center justify-center gap-2"
                    >
                      <Plus size={16} />
                      Manage Funds
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
