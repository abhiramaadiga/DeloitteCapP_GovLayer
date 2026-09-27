import React, { useState } from 'react';
import { PiggyBank, X, AlertTriangle, CheckCircle } from 'lucide-react';

export default function LiquidateFdModal({ isOpen, onClose, onLiquidate, deposit, account }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const currentAccId = String(account?.account_id || deposit?.account_id || '401');

  const handleClose = () => {
    setResult(null);
    onClose();
  };

  if (!isOpen || !deposit) return null;

  const handleConfirm = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await onLiquidate(currentAccId, deposit.deposit_id);
      setResult({
        success: true,
        message: 'Fixed Deposit Liquidated and Credited to Savings Account!',
        data: res,
      });
    } catch (err) {
      setResult({
        success: false,
        message: err.message || 'Governor Intercepted: Unauthorized FD liquidation blocked.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative text-zinc-100 popup-scale">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-purple-950/80 border border-purple-500/50 rounded-xl text-purple-400">
            <PiggyBank className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Liquidate Fixed Deposit</h2>
            <p className="text-xs text-slate-400">Premature Asset Liquidation Settlement</p>
          </div>
        </div>

        {result ? (
          <div className="space-y-4 text-xs">
            <div
              className={`p-4 rounded-xl border ${
                result.success
                  ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-200'
                  : 'bg-rose-950/80 border-rose-500/50 text-rose-200'
              }`}
            >
              <div className="flex items-center gap-2 font-bold mb-2">
                {result.success ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                )}
                <span>{result.message}</span>
              </div>
              {result.data && (
                <div className="font-mono text-[11px] space-y-1">
                  <div>Liquidated Amount: ₹{result.data.liquidated_amount_inr?.toLocaleString('en-IN')}</div>
                  <div>Status: {result.data.status}</div>
                  <div>New Balance: ₹{result.data.new_balance_inr?.toLocaleString('en-IN')}</div>
                </div>
              )}
            </div>

            <button
              onClick={handleClose}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold transition"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="space-y-4 text-xs">
            {/* Warning Box */}
            <div className="p-3 bg-amber-950/50 border border-amber-500/40 rounded-xl text-amber-200 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block">Premature Liquidation Notice</span>
                <span className="text-[11px] text-amber-300/80">
                  Premature withdrawal before March 2027 will forfeit accumulated compound interest rate of 7.25% p.a.
                </span>
              </div>
            </div>

            {/* Deposit Detail Box */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 space-y-2 font-mono">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Deposit Reference:</span>
                <span className="text-white font-bold">{deposit.deposit_id}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Principal Investment:</span>
                <span className="text-purple-400 font-bold">
                  ₹{deposit.principal_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Current Status:</span>
                <span className="text-emerald-400 font-bold">{deposit.status}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Credit Account:</span>
                <span className="text-slate-200">#{currentAccId} (Primary Savings)</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={loading || deposit.status === 'LIQUIDATED'}
                className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold flex items-center gap-2 shadow-lg shadow-purple-900/30 transition disabled:opacity-50"
              >
                {loading ? 'Processing...' : 'Confirm Liquidation'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
