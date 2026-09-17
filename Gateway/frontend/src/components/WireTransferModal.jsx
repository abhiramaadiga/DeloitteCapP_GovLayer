import React, { useState } from 'react';
import { CreditCard, X, ArrowUpRight, AlertTriangle, CheckCircle } from 'lucide-react';

export default function WireTransferModal({ isOpen, onClose, onTransfer, currentBalance, account }) {
  const currentAccId = String(account?.account_id || '401');
  const defaultDest = currentAccId === '401' ? '402' : '401';
  const [destAccount, setDestAccount] = useState(defaultDest);
  const [amount, setAmount] = useState('10000');
  const [remarks, setRemarks] = useState('Vendor wire settlement');
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [result, setResult] = useState(null);

  // Available balance safely resolves from currentBalance OR account.balance_inr
  const availableBalance =
    typeof currentBalance === 'number'
      ? currentBalance
      : typeof account?.balance_inr === 'number'
      ? account.balance_inr
      : 84250.0;

  const handleClose = () => {
    setResult(null);
    setValidationError('');
    onClose();
  };

  if (!isOpen) return null;

  const handleSelectRecipient = (accId) => {
    setDestAccount(accId);
    setValidationError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');
    setResult(null);

    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setValidationError('Please enter a valid transfer amount greater than zero.');
      return;
    }
    if (parsedAmount > availableBalance) {
      setValidationError(`Insufficient funds: Amount exceeds available balance of ₹${availableBalance.toLocaleString('en-IN')}.`);
      return;
    }
    if (destAccount === currentAccId) {
      setValidationError(`Cannot transfer funds to the same source account (#${currentAccId}).`);
      return;
    }

    setLoading(true);
    try {
      const res = await onTransfer({
        source_account: currentAccId,
        destination_account: destAccount.trim(),
        amount_inr: parsedAmount,
        remarks: remarks.trim() || 'Wire Transfer',
      });
      setResult({
        success: true,
        data: res,
        message: 'Wire Transfer Successfully Processed by Banking Core!',
      });
    } catch (err) {
      setResult({
        success: false,
        message: err.message || 'Governor Intercepted: High-risk wire transfer failed or blocked.',
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
          <div className="p-3 bg-blue-950/80 border border-blue-500/50 rounded-xl text-blue-400">
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Interbank Wire Transfer</h2>
            <p className="text-xs text-slate-400">Core Banking Finacle Direct Settlement</p>
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
                  <div>Transaction ID: {result.data.transaction_id || 'TXN-WIRE-99214A'}</div>
                  <div>Amount: ₹{parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                  <div>Recipient: Acct #{destAccount}</div>
                  <div>New Balance: ₹{(result.data.source_new_balance ?? (availableBalance - parseFloat(amount))).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
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
          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex justify-between items-center font-mono">
              <span className="text-slate-400">Available Balance:</span>
              <span className="text-emerald-400 font-bold">
                ₹{availableBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            {validationError && (
              <div className="p-3 bg-rose-950/80 border border-rose-600/50 rounded-xl text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{validationError}</span>
              </div>
            )}

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Source Account</label>
              <input
                type="text"
                value={`${account?.name || (currentAccId === '401' ? 'Rahul Sharma' : currentAccId === '402' ? 'Priya Patel' : 'Vikram Malhotra')} (#${currentAccId} - ${account?.tier || 'Gold'} Tier)`}
                disabled
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-400 font-mono"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Destination Beneficiary <span className="text-rose-400">*</span>
              </label>
              <div className="flex gap-2 mb-2">
                {[
                  { id: '401', name: 'Rahul Sharma' },
                  { id: '402', name: 'Priya Patel' },
                  { id: '403', name: 'Vikram M.' },
                ]
                  .filter((recip) => recip.id !== currentAccId)
                  .map((recip) => (
                    <button
                      key={recip.id}
                      type="button"
                      onClick={() => handleSelectRecipient(recip.id)}
                      className={`flex-1 py-1.5 px-2 rounded-lg border text-[11px] font-mono transition ${
                        destAccount === recip.id
                          ? 'bg-blue-950 border-blue-500 text-blue-300 font-bold'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      #{recip.id} ({recip.name})
                    </button>
                  ))}
              </div>
              <input
                type="text"
                value={destAccount}
                onChange={(e) => {
                  setDestAccount(e.target.value);
                  setValidationError('');
                }}
                placeholder="Enter account number (e.g. 402 or 403)"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Amount (INR ₹) <span className="text-rose-400">*</span>
              </label>
              <input
                type="number"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value);
                  setValidationError('');
                }}
                placeholder="10000"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Payment Remarks</label>
              <input
                type="text"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-blue-500"
              />
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
                type="submit"
                disabled={loading}
                className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold flex items-center gap-2 shadow-lg shadow-blue-900/30 transition disabled:opacity-50"
              >
                {loading ? (
                  <span>Executing Transfer...</span>
                ) : (
                  <>
                    <ArrowUpRight className="w-4 h-4" />
                    <span>Send Wire</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
