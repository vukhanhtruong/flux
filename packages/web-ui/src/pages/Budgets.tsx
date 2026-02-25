import { useEffect, useState } from "react";
import { Plus, Trash2, Wallet } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { Budget } from "../types";

export function Budgets() {
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
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Budgets</h1>
          <p className="text-slate-400">Set and track budget limits for your spending categories.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          {showForm ? <Trash2 size={18} /> : <Plus size={18} />}
          {showForm ? "Cancel" : "Set Budget"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="glass-card p-8 animate-in slide-in-from-top duration-500">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Category</label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                placeholder="e.g. Food, Transport, Rent"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Monthly Limit</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">$</span>
                <input
                  type="number"
                  step="0.01"
                  value={formData.monthly_limit}
                  onChange={(e) => setFormData({ ...formData, monthly_limit: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-8 pr-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                  placeholder="0.00"
                  required
                />
              </div>
            </div>
          </div>
          <div className="mt-8 flex justify-end">
            <button
              type="submit"
              className="btn-primary min-w-[120px]"
            >
              Save Budget
            </button>
          </div>
        </form>
      )}

      {budgets.length === 0 ? (
        <div className="glass-card p-20 text-center">
          <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Wallet className="w-10 h-10 text-slate-500" />
          </div>
          <p className="text-slate-500 text-lg italic">No budgets set yet. Create your first budget!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {budgets.map((budget) => (
            <div key={budget.id} className="glass-card p-8 flex flex-col hover:border-white/20 transition-all group">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold text-white group-hover:text-primary transition-colors">{budget.category}</h3>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-3xl font-black text-white">${parseFloat(budget.monthly_limit).toLocaleString()}</span>
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">/mo</span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(budget.id)}
                  className="p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                  title="Delete"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <div className="mt-auto space-y-3">
                <div className="h-2.5 w-full rounded-full bg-white/5 overflow-hidden border border-white/5">
                  <div className="h-full rounded-full bg-primary/40" style={{ width: "0%" }} />
                </div>
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-tighter text-slate-500">
                  <span>0% Spent</span>
                  <span className="text-slate-400">Spending data available in Reports</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
