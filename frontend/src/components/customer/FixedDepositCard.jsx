import React from 'react';
import { PiggyBank, ArrowRight, Lock, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';
import Tooltip from '../common/Tooltip';

export default function FixedDepositCard({
  deposits,
  account,
  onOpenLiquidate,
}) {
  const currentAccId = account?.account_id || deposits?.account_id || '401';
  const rawList = deposits?.deposits || [];
  const totalPrincipal = deposits?.total_deposits_inr ?? rawList
    .filter((d) => d.status !== 'LIQUIDATED')
    .reduce((sum, d) => sum + (d.principal_inr || 0), 0);

  const activeCount = rawList.filter((d) => d.status !== 'LIQUIDATED').length;

  return (
    <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-5 sm:p-6 shadow-xl relative overflow-hidden backdrop-blur space-y-4">
      {/* Portfolio Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-950/70 border border-indigo-700/50 text-indigo-400">
            <PiggyBank className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                Term Deposits Portfolio
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950 border border-indigo-700/60 text-indigo-300 font-bold">
                {activeCount} Active FD{activeCount === 1 ? '' : 's'}
              </span>
            </div>
            <p className="text-xs text-zinc-400 font-mono mt-0.5">
              Custody Account #{currentAccId} • Compound Interest Accrual
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-right">
          <div className="bg-zinc-950 px-3.5 py-2 rounded-xl border border-zinc-800">
            <span className="text-[10px] text-zinc-500 uppercase font-mono block">Total Portfolio Principal</span>
            <span className="text-sm sm:text-base font-bold text-emerald-400 font-mono tabular-nums">
              ₹{totalPrincipal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </div>

      {/* Multiple FD Cards Grid */}
      {rawList.length === 0 ? (
        <div className="p-6 text-center text-zinc-500 font-mono text-xs bg-zinc-950/60 rounded-xl border border-zinc-800/60">
          No fixed deposits found for Account #{currentAccId}.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rawList.map((deposit) => {
            const isLiquidated = deposit.status === 'LIQUIDATED';
            return (
              <div
                key={deposit.deposit_id}
                className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
                  isLiquidated
                    ? 'bg-zinc-950/40 border-zinc-800/50 opacity-60'
                    : 'bg-zinc-950/80 border-zinc-800 hover:border-zinc-700 shadow-md'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-indigo-950/60 border border-indigo-800/60 flex items-center justify-center text-indigo-300 font-mono text-xs">
                        <Layers className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white block truncate max-w-[180px]">
                          {deposit.type || 'Fixed Deposit'}
                        </span>
                        <span className="text-[10px] font-mono text-zinc-500">
                          Ref: {deposit.deposit_id}
                        </span>
                      </div>
                    </div>

                    <span
                      className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-md border flex items-center gap-1 ${
                        isLiquidated
                          ? 'bg-zinc-900 border-zinc-700 text-zinc-400'
                          : 'bg-emerald-950/80 border-emerald-500/40 text-emerald-300'
                      }`}
                    >
                      {isLiquidated ? (
                        <CheckCircle2 className="w-2.5 h-2.5" />
                      ) : (
                        <Lock className="w-2.5 h-2.5 text-emerald-400" />
                      )}
                      <span>{isLiquidated ? 'LIQUIDATED' : 'LOCKED'}</span>
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 py-2.5 border-y border-zinc-850 font-mono text-xs">
                    <div>
                      <span className="text-[9px] text-zinc-500 uppercase block">Principal</span>
                      <span className="text-xs font-bold text-zinc-100 tabular-nums">
                        ₹{deposit.principal_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-zinc-500 uppercase block">Annual Yield</span>
                      <span className="text-xs font-bold text-indigo-400">
                        {deposit.interest_rate} Compounded
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-zinc-500 uppercase block">Maturity Date</span>
                      <span className="text-[11px] text-zinc-300">
                        {deposit.maturity_date}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-zinc-500 uppercase block">Linked Account</span>
                      <span className="text-[11px] text-zinc-400">
                        #{currentAccId} (Savings)
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-1">
                  <Tooltip
                    content={
                      isLiquidated
                        ? `Deposit ${deposit.deposit_id} already settled into #${currentAccId}`
                        : `Premature liquidation of ${deposit.deposit_id} triggers 1.5% regulatory penalty`
                    }
                    position="top"
                    className="w-full"
                  >
                    <button
                      type="button"
                      onClick={() => onOpenLiquidate && onOpenLiquidate(deposit)}
                      disabled={isLiquidated}
                      className={`w-full py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                        isLiquidated
                          ? 'bg-zinc-900 border border-zinc-800 text-zinc-500 cursor-not-allowed'
                          : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-200 hover:text-white border border-zinc-700 hover:border-zinc-600 hover-lift'
                      }`}
                    >
                      {isLiquidated ? (
                        <span>Settled into #{currentAccId}</span>
                      ) : (
                        <>
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          <span>Liquidate {deposit.deposit_id}</span>
                          <ArrowRight className="w-3 h-3 ml-auto text-zinc-500" />
                        </>
                      )}
                    </button>
                  </Tooltip>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
