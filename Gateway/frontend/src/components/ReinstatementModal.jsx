import React, { useState } from 'react';
import { ShieldCheck, X, AlertTriangle, CheckCircle } from 'lucide-react';

export default function ReinstatementModal({
  agent,
  isOpen,
  onClose,
  onConfirm,
  onConfirmReinstate,
}) {
  const [analystId, setAnalystId] = useState('SOC-ANALYST-PES-4091');
  const [justification, setJustification] = useState('');
  const [certified, setCertified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen || !agent) return null;

  const confirmFn = onConfirm || onConfirmReinstate;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!justification.trim() || justification.trim().length < 5) {
      setError('FFIEC Regulatory Requirement: Justification must be at least 5 characters.');
      return;
    }
    if (!certified) {
      setError('You must certify compliance with FFIEC Cat-3 remediation protocol.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      if (confirmFn) {
        await confirmFn(agent.agent_id, justification.trim(), analystId.trim());
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to reinstate agent.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative text-zinc-100 popup-scale">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-emerald-950/80 border border-emerald-500/50 rounded-xl text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">FFIEC Reinstatement Protocol</h2>
            <p className="text-xs text-slate-400">
              Revoke Kill-Switch & Re-issue Cryptographic Agent Passport
            </p>
          </div>
        </div>

        {/* Target Agent Info Box */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 mb-4 text-xs font-mono">
          <div className="flex justify-between items-center mb-1">
            <span className="text-slate-400">Target Non-Human Identity:</span>
            <span className="text-rose-400 font-bold">{agent.agent_id}</span>
          </div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-slate-400">Assigned Role:</span>
            <span className="text-slate-200">{agent.role}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Current PEP State:</span>
            <span className="px-2 py-0.5 rounded bg-rose-950/80 border border-rose-500/50 text-rose-300 font-bold text-[10px]">
              QUARANTINED
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {/* Analyst ID */}
          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Lead SOC Analyst ID <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={analystId}
              onChange={(e) => setAnalystId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-white font-mono focus:outline-none focus:border-emerald-500 transition"
              required
            />
          </div>

          {/* Justification */}
          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Mandatory Regulatory Justification & Audit Note <span className="text-rose-400">*</span>
            </label>
            <textarea
              rows={3}
              value={justification}
              onChange={(e) => {
                setJustification(e.target.value);
                if (error) setError('');
              }}
              placeholder="e.g. Threat quarantined, false positive confirmed via XAI causal analysis; prompt boundary retrained."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 transition"
              required
            />
            <span className="text-[10px] text-slate-500">
              Min 5 characters required for SOX-404 audit trail compliance.
            </span>
          </div>

          {/* Compliance Checkbox */}
          <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl flex items-start gap-2.5">
            <input
              type="checkbox"
              id="certify"
              checked={certified}
              onChange={(e) => setCertified(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
            />
            <label htmlFor="certify" className="text-[11px] text-slate-300 leading-relaxed cursor-pointer">
              I certify that this Autonomous AI Agent has undergone behavioral sandbox re-verification and conforms with FFIEC Cat-3 Non-Human Identity Governance standards.
            </label>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-rose-950/80 border border-rose-600/50 rounded-lg text-rose-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold flex items-center gap-2 shadow-lg shadow-emerald-900/30 transition disabled:opacity-50"
            >
              {loading ? (
                <span>Reinstating...</span>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Lift Quarantine</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
