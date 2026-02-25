import { useEffect, useState } from "react";
import { Plus, Trash2, CalendarRange } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import type { Subscription } from "../types";

export function Subscriptions() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    amount: "",
    billing_cycle: "monthly",
    next_date: new Date().toISOString().split("T")[0],
    category: "Utilities",
  });

  async function fetchSubscriptions() {
    try {
      const data = await api.listSubscriptions(USER_ID);
      setSubscriptions(data);
    } catch (error) {
      console.error("Failed to fetch subscriptions:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.createSubscription({
        user_id: USER_ID,
        name: formData.name,
        amount: parseFloat(formData.amount),
        billing_cycle: formData.billing_cycle,
        next_date: formData.next_date,
        category: formData.category,
      });
      setShowForm(false);
      setFormData({
        name: "",
        amount: "",
        billing_cycle: "monthly",
        next_date: new Date().toISOString().split("T")[0],
        category: "Utilities",
      });
      await fetchSubscriptions();
    } catch (error) {
      console.error("Failed to create subscription:", error);
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteSubscription(id, USER_ID);
      await fetchSubscriptions();
    } catch (error) {
      console.error("Failed to delete subscription:", error);
    }
  }

  const totalMonthly = subscriptions.reduce((sum, sub) => {
    const amount = parseFloat(sub.amount);
    return sum + (sub.billing_cycle === "yearly" ? amount / 12 : amount);
  }, 0);

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Subscriptions</h1>
          <p className="text-slate-400">Manage your recurring payments and digital services.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          {showForm ? <Trash2 size={18} /> : <Plus size={18} />}
          {showForm ? "Cancel" : "Add Subscription"}
        </button>
      </div>

      {subscriptions.length > 0 && (
        <div className="glass-card p-8 border-l-4 border-l-secondary">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-secondary/10 rounded-xl">
              <CalendarRange className="w-8 h-8 text-secondary" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1">Total Monthly Liability</p>
              <p className="text-4xl font-black text-white">${totalMonthly.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            </div>
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="glass-card p-8 animate-in slide-in-from-top duration-500">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Service Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                placeholder="e.g. Netflix, Spotify"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Amount</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">$</span>
                <input
                  type="number"
                  step="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-8 pr-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                  placeholder="0.00"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Billing Cycle</label>
              <select
                value={formData.billing_cycle}
                onChange={(e) => setFormData({ ...formData, billing_cycle: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-1.5 h-[46px] text-white outline-none focus:border-primary/50 transition-colors"
              >
                <option value="monthly" className="bg-dark">Monthly</option>
                <option value="yearly" className="bg-dark">Yearly</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-1.5 h-[46px] text-white outline-none focus:border-primary/50 transition-colors"
              >
                <option value="Utilities" className="bg-dark">Utilities</option>
                <option value="Entertainment" className="bg-dark">Entertainment</option>
                <option value="Health" className="bg-dark">Health</option>
                <option value="Shopping" className="bg-dark">Shopping</option>
                <option value="Other" className="bg-dark">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Next Billing Date</label>
              <input
                type="date"
                value={formData.next_date}
                onChange={(e) => setFormData({ ...formData, next_date: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                required
              />
            </div>
          </div>
          <div className="mt-8 flex justify-end">
            <button
              type="submit"
              className="btn-primary min-w-[120px]"
            >
              Save Subscription
            </button>
          </div>
        </form>
      )}

      <div className="glass-card overflow-hidden">
        <div className="px-8 py-6 border-b border-white/5 bg-white/5">
          <h2 className="text-xl font-bold text-white">Active Subscriptions</h2>
        </div>
        {subscriptions.length === 0 ? (
          <div className="px-8 py-16 text-center">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <CalendarRange className="w-8 h-8 text-slate-500" />
            </div>
            <p className="text-slate-500 italic">No subscriptions yet. Add your first one!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Service</th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Cycle</th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Next Billing</th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Amount</th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {subscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-white group-hover:text-secondary transition-colors">{sub.name}</span>
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{sub.category}</span>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-white/5 text-slate-400 border border-white/10">
                        {sub.billing_cycle}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-sm text-slate-400">
                      {new Date(sub.next_date).toLocaleDateString()}
                    </td>
                    <td className="px-8 py-5 text-sm font-bold text-white text-right">
                      ${parseFloat(sub.amount).toLocaleString()}
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button
                        onClick={() => handleDelete(sub.id)}
                        className="p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
