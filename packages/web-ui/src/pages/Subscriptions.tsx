import { useEffect, useState } from "react";
import { CalendarRange } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDate } from "../lib/format";
import type { Subscription } from "../types";

export function Subscriptions() {
  const { profile } = useProfile();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);

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

  const totalMonthly = subscriptions.reduce((sum, sub) => {
    const amount = parseFloat(sub.amount);
    return sum + (sub.billing_cycle === "yearly" ? amount / 12 : amount);
  }, 0);

  if (loading) {
    return <div className="text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Subscriptions</h1>
          <p className="text-slate-400">Manage your recurring subscriptions and payments.</p>
        </div>
      </div>

      {subscriptions.length > 0 && (
        <div className="glass-card p-4 md:p-6 lg:p-8 border-l-4 border-l-secondary mb-10">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-secondary/10 rounded-xl">
              <CalendarRange className="w-8 h-8 text-secondary" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1">
                Total Monthly Liability
              </p>
              <p className="text-4xl font-black text-white">
                {formatCurrency(totalMonthly, profile.currency, profile.locale)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <div className="px-4 md:px-6 lg:px-8 py-5 md:py-6 border-b border-white/5 bg-white/5">
          <h2 className="text-xl font-bold text-white">Active Subscriptions</h2>
        </div>
        {subscriptions.length === 0 ? (
          <div className="px-4 md:px-8 py-12 md:py-16 text-center">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <CalendarRange className="w-8 h-8 text-slate-500" />
            </div>
            <p className="text-slate-500 italic">No subscriptions yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Service
                  </th>
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Cycle
                  </th>
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Next Billing
                  </th>
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {subscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-white group-hover:text-secondary transition-colors">
                          {sub.name}
                        </span>
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                          {sub.category}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-white/5 text-slate-400 border border-white/10">
                        {sub.billing_cycle}
                      </span>
                    </td>
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5 whitespace-nowrap text-sm text-slate-400">
                      {formatDate(sub.next_date, profile.locale, profile.timezone)}
                    </td>
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5 whitespace-nowrap text-sm font-bold text-white text-right">
                      {formatCurrency(sub.amount, profile.currency, profile.locale)}
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
