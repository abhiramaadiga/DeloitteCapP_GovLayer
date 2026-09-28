import React, { useState } from 'react';
import {
  Landmark,
  ShieldCheck,
  User,
  Lock,
  ArrowRight,
  CreditCard,
  Shield,
  Eye,
  EyeOff,
  AlertCircle,
  Sparkles,
  Loader2,
} from 'lucide-react';
import Tooltip from './common/Tooltip';
import { loginUser } from '../services/api';

export default function LoginView({ onLogin }) {
  // Active Tab: 'customer' | 'admin'
  const [activeTab, setActiveTab] = useState('customer');

  const [username, setUsername] = useState('rahul');
  const [password, setPassword] = useState('banking123');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Synchronize defaults when switching tabs
  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    setError('');
    if (tab === 'customer') {
      setUsername('rahul');
      setPassword('banking123');
    } else {
      setUsername('admin');
      setPassword('soc2026');
    }
  };

  // Automatically detect role intent as user types username
  const handleUsernameChange = (val) => {
    setUsername(val);
    const lower = val.trim().toLowerCase();
    const adminIdentifiers = ['admin', 'soc', 'analyst', 'secops', 'governor', 'compliance', 'deloitte', 'audit'];
    if (adminIdentifiers.some((kw) => lower.includes(kw))) {
      setActiveTab('admin');
    } else if (
      lower.includes('rahul') ||
      lower.includes('401') ||
      lower.includes('priya') ||
      lower.includes('vikram') ||
      lower.includes('customer') ||
      lower.includes('user')
    ) {
      setActiveTab('customer');
    }
  };

  const executeLogin = async (roleType, uOverride, pOverride) => {
    setError('');
    setIsSubmitting(true);
    const u = (uOverride || (roleType === 'admin' ? 'admin' : 'rahul')).trim().toLowerCase();
    const p = (pOverride || (roleType === 'admin' ? 'soc2026' : 'banking123')).trim();

    try {
      const authRes = await loginUser(u, p);
      if (authRes?.user) {
        onLogin(authRes.user);
      } else {
        throw new Error('Authentication response invalid.');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const u = username.trim().toLowerCase();
    const p = password.trim();

    if (!u || !p) {
      setError('Please provide corporate identifier and credential password.');
      return;
    }

    // Dynamic role determination based on entered credentials
    const adminIdentifiers = ['admin', 'soc', 'analyst', 'secops', 'governor', 'compliance', 'deloitte', 'audit'];
    const adminPasswords = ['soc2026', 'admin', 'admin123', 'deloitte_secure_pass'];

    const isAdmin =
      adminIdentifiers.some((kw) => u.includes(kw)) ||
      adminPasswords.includes(p.toLowerCase()) ||
      activeTab === 'admin';

    executeLogin(isAdmin ? 'admin' : 'customer', u, p);
  };


  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col justify-between selection:bg-indigo-600 selection:text-white relative overflow-hidden font-sans">
      {/* Background Architectural Grid & Subtle Atmospheric Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:24px_24px] opacity-25 pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[320px] bg-gradient-to-b from-indigo-600/10 via-purple-600/5 to-transparent blur-3xl pointer-events-none" />

      {/* Corporate Header */}
      <header className="relative z-10 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-700/80 flex items-center justify-center text-emerald-400 shadow-md">
              <Landmark className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-tight text-white text-base">
                  APEX COMMERCIAL BANK
                </span>
                <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  BFSI CORE
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Enterprise Banking & Autonomous Security Infrastructure
              </p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-zinc-400 bg-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-800">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>PEP GATEWAY :8000</span>
          </div>
        </div>
      </header>

      {/* Main Authentication Card */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Header Title */}
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Unified Workforce & Identity Access</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Institutional Sign In
            </h1>
            <p className="text-xs sm:text-sm text-zinc-400">
              Select your role partition to access your authorized console
            </p>
          </div>

          {/* Segmented Controller Tab Switcher */}
          <div className="bg-zinc-900/90 p-1.5 rounded-2xl border border-zinc-800 grid grid-cols-2 gap-1.5 shadow-inner backdrop-blur">
            <button
              type="button"
              onClick={() => handleTabSwitch('customer')}
              className={`py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all hover-lift ${
                activeTab === 'customer'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/60'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <CreditCard className="w-4 h-4" />
              <span>Retail Client</span>
            </button>

            <button
              type="button"
              onClick={() => handleTabSwitch('admin')}
              className={`py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all hover-lift ${
                activeTab === 'admin'
                  ? 'bg-rose-600 text-white shadow-md shadow-rose-950/60'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>Cyber SOC Admin</span>
            </button>
          </div>

          {/* Login Box */}
          <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-6 sm:p-7 shadow-2xl backdrop-blur card-hover popup-scale">
            {error && (
              <div className="mb-4 p-3 rounded-xl bg-rose-950/80 border border-rose-600/60 text-rose-200 text-xs flex items-center gap-2 animate-fadeIn">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Quick One-Click Multi-User Profiles */}
            <div className="mb-5 space-y-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-bold block">
                {activeTab === 'admin' ? 'Instant Sign-In Profile:' : 'Select Customer Account to Test:'}
              </span>
              {activeTab === 'admin' ? (
                <button
                  type="button"
                  onClick={() => executeLogin('admin', 'admin', 'soc2026')}
                  disabled={isSubmitting}
                  className="w-full py-2.5 px-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center justify-between shadow-lg shadow-rose-950/60 transition hover-lift disabled:opacity-50"
                >
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    <span>SOC Lead Auditor (admin)</span>
                  </div>
                  <span className="font-mono text-[10px] bg-rose-950/80 px-2 py-0.5 rounded border border-rose-400/40">Tier-4 Lead</span>
                </button>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => executeLogin('customer', 'rahul', 'banking123')}
                    disabled={isSubmitting}
                    className="p-2.5 rounded-xl bg-indigo-950/80 hover:bg-indigo-900/90 border border-indigo-700/60 text-left transition hover-lift disabled:opacity-50"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-white font-bold text-xs">Rahul</span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-700">GOLD</span>
                    </div>
                    <p className="text-[10px] text-zinc-400 font-mono mt-0.5">#401 • ₹84.2k</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => executeLogin('customer', 'priya', 'banking123')}
                    disabled={isSubmitting}
                    className="p-2.5 rounded-xl bg-purple-950/80 hover:bg-purple-900/90 border border-purple-700/60 text-left transition hover-lift disabled:opacity-50"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-white font-bold text-xs">Priya</span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-700">PLATINUM</span>
                    </div>
                    <p className="text-[10px] text-zinc-400 font-mono mt-0.5">#402 • ₹312.4k</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => executeLogin('customer', 'vikram', 'banking123')}
                    disabled={isSubmitting}
                    className="p-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-850 border border-zinc-700 text-left transition hover-lift disabled:opacity-50"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-white font-bold text-xs">Vikram</span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 border border-zinc-600">SILVER</span>
                    </div>
                    <p className="text-[10px] text-zinc-400 font-mono mt-0.5">#403 • ₹15.0k</p>
                  </button>
                </div>
              )}
            </div>

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-800" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-zinc-900 px-2 text-zinc-500 font-mono">
                  Or enter credentials (DB Verified)
                </span>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-zinc-300 font-mono uppercase tracking-wider">
                  {activeTab === 'admin' ? 'Security Analyst ID' : 'Account Identifier'}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => handleUsernameChange(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 font-mono transition"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-zinc-300 font-mono uppercase tracking-wider">
                  Security Passcode
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-10 py-2 text-xs text-white placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 font-mono transition"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-zinc-500 hover:text-zinc-300"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold text-xs transition hover-lift flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Verifying JWT Credentials...</span>
                  </>
                ) : (
                  <>
                    <span>Authenticate Session</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>


              {/* Credential Routing Guide */}
              <div className="pt-2 border-t border-zinc-800/80 text-[11px] font-mono text-zinc-400 space-y-1.5">
                <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">Database Seeded Accounts:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  <div className="flex items-center justify-between px-2.5 py-1 rounded-lg bg-zinc-950/60 border border-zinc-800">
                    <span className="text-zinc-400">#401 (Rahul):</span>
                    <span className="text-indigo-400 font-bold">rahul / banking123</span>
                  </div>
                  <div className="flex items-center justify-between px-2.5 py-1 rounded-lg bg-zinc-950/60 border border-zinc-800">
                    <span className="text-zinc-400">#402 (Priya):</span>
                    <span className="text-purple-400 font-bold">priya / banking123</span>
                  </div>
                  <div className="flex items-center justify-between px-2.5 py-1 rounded-lg bg-zinc-950/60 border border-zinc-800">
                    <span className="text-zinc-400">#403 (Vikram):</span>
                    <span className="text-zinc-300 font-bold">vikram / banking123</span>
                  </div>
                  <div className="flex items-center justify-between px-2.5 py-1 rounded-lg bg-zinc-950/60 border border-zinc-800">
                    <span className="text-zinc-400">SOC Admin:</span>
                    <span className="text-rose-400 font-bold">admin / soc2026</span>
                  </div>
                </div>
              </div>
            </form>
          </div>

          {/* Security Notice */}
          <div className="text-center text-[11px] text-zinc-500 font-mono space-y-1">
            <div className="flex items-center justify-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>FastAPI PEP :8000 End-to-End Verified</span>
              <span>•</span>
              <span>SOX-404 Audited</span>
            </div>
            <p className="text-zinc-600">
              Deloitte Capstone 2026 • Autonomous Agent Security & Governance Platform
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-zinc-900 bg-zinc-950/90 px-6 py-3 text-center text-xs text-zinc-600 font-mono">
        Apex Commercial Bank Information Security Operations Command • Tamper-evident ledger enabled
      </footer>
    </div>
  );
}
