import React from 'react';
import { RefreshCw, ShieldCheck, TrendingUp } from 'lucide-react';
import Tooltip from '../common/Tooltip';

export default function BalanceHero({
  account,
  deposits,
  onRefresh,
  refreshing,
}) {
  const balance = typeof account?.balance_inr === 'number' ? account.balance_inr : 84250.0;
  const fdItem = deposits?.deposits?.[0] || {
    principal_inr: 500000.0,
    status: 'LOCKED',
  };
  const isLiquidated = fdItem.status === 'LIQUIDATED' || deposits?.total_deposits_inr === 0;
  const totalFd =
    typeof deposits?.total_deposits_inr === 'number'
      ? deposits.total_deposits_inr
      : isLiquidated
      ? 0.0
      : (fdItem.principal_inr ?? 500000.0);
  const totalNetWorth = balance + (isLiquidated ? 0.0 : totalFd);

  return (
    <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-6 shadow-xl card-hover relative overflow-hidden backdrop-blur">
      {/* Subtle top atmospheric glow */}
      <div className="absolute top-0 right-0 w-64 h-32 bg-indigo-600/10 blur-3xl pointer-events-none" />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-mono uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Verified Core Finacle
            </span>
            <span className="text-[11px] font-mono text-zinc-500">
              Account #{account?.account_id || '401'}
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white">
            Primary Savings Portfolio
          </h2>
        </div>

        {/* Live Sync Trigger */}
        <Tooltip content="Synchronize live ledger balance with Core Banking Gateway (:8000)" position="left">
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/80 text-xs font-semibold transition hover-lift disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-indigo-400' : 'text-zinc-400'}`} />
            <span>{refreshing ? 'Syncing...' : 'Sync Balance'}</span>
          </button>
        </Tooltip>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-zinc-800/80">
        {/* Available Liquidity */}
        <div>
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
            Available Operating Balance
          </p>
          <div className="flex items-baseline gap-2 mt-1.5">
            <span className="text-3xl sm:text-4xl font-black text-white font-mono tracking-tight tabular-nums">
              ₹{balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-xs font-mono text-emerald-400 font-semibold">
              INR Liquid
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 mt-1 flex items-center gap-1 font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Zero-Trust Fast-Path PEP Guarded
          </p>
        </div>

        {/* Total Assets / Net Worth */}
        <div className="border-t md:border-t-0 md:border-l border-zinc-800/80 pt-4 md:pt-0 md:pl-6">
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider flex items-center justify-between">
            <span>Total Combined Net Worth</span>
            <span className="text-[10px] font-mono text-zinc-500">Savings + Fixed Deposit</span>
          </p>
          <div className="flex items-baseline gap-2 mt-1.5">
            <span className="text-2xl sm:text-3xl font-bold text-zinc-200 font-mono tracking-tight tabular-nums">
              ₹{totalNetWorth.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-xs font-mono text-indigo-400 flex items-center gap-1 font-semibold">
              <TrendingUp className="w-3 h-3" />
              +7.25% p.a.
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 mt-1 font-mono">
            Includes ₹{(totalFd).toLocaleString('en-IN')} Term Asset (#FD-901)
          </p>
        </div>
      </div>
    </div>
  );
}
