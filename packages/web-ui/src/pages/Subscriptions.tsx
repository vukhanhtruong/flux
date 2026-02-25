import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Subscription } from "../types";

export function Subscriptions() {
  const { profile } = useProfile();
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Subscriptions</h1>
          <p className="mt-2 text-gray-600">Manage your recurring subscriptions and payments.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus size={18} />
          Add Subscription
        </button>
      </div>

      {subscriptions.length > 0 && (
        <div className="rounded-lg bg-white p-6 shadow">
          <h3 className="text-sm font-medium text-gray-500">Total Monthly Cost</h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900">
            {formatCurrency(totalMonthly, profile.currency, profile.locale)}
          </p>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-lg bg-white p-6 shadow">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="e.g. Netflix"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="0.00"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Billing Cycle</label>
              <select
                value={formData.billing_cycle}
                onChange={(e) => setFormData({ ...formData, billing_cycle: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="Utilities">Utilities</option>
                <option value="Entertainment">Entertainment</option>
                <option value="Health">Health</option>
                <option value="Shopping">Shopping</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Next Billing Date</label>
              <input
                type="date"
                value={formData.next_date}
                onChange={(e) => setFormData({ ...formData, next_date: e.target.value })}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
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

      <div className="rounded-lg bg-white shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">All Subscriptions</h2>
        </div>
        {subscriptions.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            No subscriptions yet. Add your first one!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500">Name</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500 text-right">Amount</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500">Billing Cycle</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500">Next Billing</th>
                  <th className="px-6 py-3 text-sm font-medium text-gray-500 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {subscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{sub.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 text-right">
                      {formatCurrency(sub.amount, profile.currency, profile.locale)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 capitalize">{sub.billing_cycle}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDate(sub.next_date, profile.locale, profile.timezone)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(sub.id)}
                        className="text-red-500 hover:text-red-700"
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
