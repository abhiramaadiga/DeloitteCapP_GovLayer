import React, { useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Search, Receipt } from 'lucide-react';

export default function TransactionLedger({ transactions = [] }) {
  const [filter, setFilter] = useState('');

  const fallbackTransactions = [
    {
      id: 'TXN-98214',
      date: 'Today, 09:15 AM',
      description: 'Tata Consultancy Payroll Direct Credit',
      category: 'Salary',
      amount: 145000.0,
      type: 'credit',
      status: 'Settled',
    },
    {
      id: 'TXN-98190',
      date: 'Yesterday, 18:40 PM',
      description: 'UPI Merchant Settlement (Blinkit Groceries)',
      category: 'Merchant',
      amount: 2450.0,
      type: 'debit',
      status: 'Settled',
    },
    {
      id: 'TXN-98012',
      date: '12 Sep 2026',
      description: 'Apex Commercial ATM Cash Withdrawal (Indiranagar)',
      category: 'Cash',
      amount: 10000.0,
      type: 'debit',
      status: 'Settled',
    },
    {
      id: 'TXN-97940',
      date: '10 Sep 2026',
      description: 'Quarterly Fixed Deposit Interest Settlement (#FD-901)',
      category: 'Interest',
      amount: 9062.5,
      type: 'credit',
      status: 'Settled',
    },
  ];

  const items = transactions.length > 0 ? transactions : fallbackTransactions;
  const filtered = items.filter(
    (t) =>
      t.description.toLowerCase().includes(filter.toLowerCase()) ||
      t.id.toLowerCase().includes(filter.toLowerCase()) ||
      t.category.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-5 shadow-xl card-hover relative overflow-hidden backdrop-blur">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-zinc-800 text-zinc-300">
            <Receipt className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Recent Account Activity</h3>
            <p className="text-[11px] text-zinc-400 font-mono">
              Immutable Ledger • Account #401
            </p>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-56">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search activity..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500 transition font-sans"
          />
        </div>
      </div>

      {/* Transactions List */}
      <div className="divide-y divide-zinc-800/60">
        {filtered.length === 0 ? (
          <div className="py-8 text-center text-xs text-zinc-500 font-mono">
            No matching transactions found
          </div>
        ) : (
          filtered.map((txn) => {
            const isCredit = txn.type === 'credit';
            return (
              <div
                key={txn.id}
                className="py-3 px-2 flex items-center justify-between gap-3 hover:bg-zinc-800/40 rounded-xl transition"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs shrink-0 ${
                      isCredit
                        ? 'bg-emerald-950/60 border border-emerald-500/30 text-emerald-400'
                        : 'bg-zinc-800 border border-zinc-700/60 text-zinc-400'
                    }`}
                  >
                    {isCredit ? <ArrowDownLeft className="w-4 h-4" /> : <ArrowUpRight className="w-4 h-4" />}
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-zinc-200">
                      {txn.description}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5 text-[10px] text-zinc-500 font-mono">
                      <span>{txn.date}</span>
                      <span>•</span>
                      <span>{txn.category}</span>
                      <span>•</span>
                      <span className="text-zinc-400">{txn.id}</span>
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span
                    className={`text-xs font-bold font-mono tabular-nums block ${
                      isCredit ? 'text-emerald-400' : 'text-zinc-200'
                    }`}
                  >
                    {isCredit ? '+' : '-'}₹{txn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500">
                    {txn.status || 'Settled'}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
