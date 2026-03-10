import { useEffect, useState } from "react";
import { ArrowRightLeft } from "lucide-react";
import { api } from "../lib/api";
import { USER_ID } from "../lib/constants";
import { useProfile } from "../context/ProfileContext";
import { formatCurrency, formatDateTime } from "../lib/format";
import type { Transaction } from "../types";

export function Transactions() {
  const { profile } = useProfile();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

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
      </div>

      <div className="glass-card overflow-hidden">
        <div className="px-4 md:px-6 lg:px-8 py-5 md:py-6 border-b border-white/5 bg-white/5">
          <h2 className="text-xl font-bold text-white">All Transactions</h2>
        </div>
        {transactions.length === 0 ? (
          <div className="px-4 md:px-8 py-12 md:py-16 text-center">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <ArrowRightLeft className="w-8 h-8 text-slate-500" />
            </div>
            <p className="text-slate-500 italic">No transactions yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 md:px-6 lg:px-8 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {transactions.map((txn) => (
                  <tr key={txn.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5 text-sm text-slate-300 whitespace-nowrap">
                      {formatDateTime(txn.date, profile.locale, profile.timezone)}
                    </td>
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5">
                      <p className="text-sm font-semibold text-white group-hover:text-primary transition-colors whitespace-nowrap">
                        {txn.description}
                      </p>
                    </td>
                    <td className="px-4 md:px-6 lg:px-8 py-4 md:py-5">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/5 text-slate-400 border border-white/10 whitespace-nowrap">
                        {txn.category}
                      </span>
                    </td>
                    <td
                      className={`px-4 md:px-6 lg:px-8 py-4 md:py-5 text-sm font-bold text-right whitespace-nowrap ${txn.type === "income" ? "text-emerald-400" : "text-slate-200"
                        }`}
                    >
                      {txn.type === "income" ? "+" : "-"}
                      {formatCurrency(txn.amount, profile.currency, profile.locale)}
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
