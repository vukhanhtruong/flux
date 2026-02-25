import { useEffect, useState } from "react";
import { Plus, Trash2, ArrowRightLeft } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Transaction, TransactionCreate, TransactionType } from "../types";

export function Transactions() {
  const { profile } = useProfile();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    amount: "",
    category: "",
    description: "",
    type: "expense" as TransactionType,
  });

  async function fetchTransactions() {
    try {
      const data = await api.listTransactions(USER_ID);
      setTransactions(data);
    } catch (error) {
      console.error("Failed to fetch transactions:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchTransactions();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: TransactionCreate = {
      user_id: USER_ID,
      date: formData.date,
      amount: parseFloat(formData.amount),
      category: formData.category,
      description: formData.description,
      type: formData.type,
    };
    try {
      await api.createTransaction(payload);
      setShowForm(false);
      setFormData({
        date: new Date().toISOString().split("T")[0],
        amount: "",
        category: "",
        description: "",
        type: "expense",
      });
      await fetchTransactions();
    } catch (error) {
      console.error("Failed to create transaction:", error);
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteTransaction(id, USER_ID);
      await fetchTransactions();
    } catch (error) {
      console.error("Failed to delete transaction:", error);
    }
  }

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Transactions</h1>
          <p className="text-slate-400">View and manage your income and expenses.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          {showForm ? <Trash2 size={18} /> : <Plus size={18} />}
          {showForm ? "Cancel" : "Add Transaction"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="glass-card p-8 animate-in slide-in-from-top duration-500 mb-10"
        >
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Date
              </label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Amount
              </label>
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
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Category
              </label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                placeholder="e.g. Food, Transport"
                required
              />
            </div>
            <div className="lg:col-span-2">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Description
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white outline-none focus:border-primary/50 transition-colors"
                placeholder="What was this for?"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Type
              </label>
              <select
                value={formData.type}
                onChange={(e) =>
                  setFormData({ ...formData, type: e.target.value as TransactionType })
                }
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-1.5 h-[46px] text-white outline-none focus:border-primary/50 transition-colors"
              >
                <option value="expense" className="bg-dark">
                  Expense
                </option>
                <option value="income" className="bg-dark">
                  Income
                </option>
              </select>
            </div>
          </div>
          <div className="mt-8 flex justify-end">
            <button type="submit" className="btn-primary min-w-[120px]">
              Save
            </button>
          </div>
        </form>
      )}

      <div className="glass-card overflow-hidden">
        <div className="px-8 py-6 border-b border-white/5 bg-white/5">
          <h2 className="text-xl font-bold text-white">All Transactions</h2>
        </div>
        {transactions.length === 0 ? (
          <div className="px-8 py-16 text-center">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <ArrowRightLeft className="w-8 h-8 text-slate-500" />
            </div>
            <p className="text-slate-500 italic">No transactions yet. Add your first one!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                    Amount
                  </th>
                  <th className="px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {transactions.map((txn) => (
                  <tr key={txn.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-8 py-5 text-sm text-slate-300">
                      {formatDate(txn.date, profile.locale, profile.timezone)}
                    </td>
                    <td className="px-8 py-5">
                      <p className="text-sm font-semibold text-white group-hover:text-primary transition-colors">
                        {txn.description}
                      </p>
                    </td>
                    <td className="px-8 py-5">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/5 text-slate-400 border border-white/10">
                        {txn.category}
                      </span>
                    </td>
                    <td
                      className={`px-8 py-5 text-sm font-bold text-right ${txn.type === "income" ? "text-emerald-400" : "text-slate-200"
                        }`}
                    >
                      {txn.type === "income" ? "+" : "-"}
                      {formatCurrency(txn.amount, profile.currency, profile.locale)}
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button
                        onClick={() => handleDelete(txn.id)}
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
