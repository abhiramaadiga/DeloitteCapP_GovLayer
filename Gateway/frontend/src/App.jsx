import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import CustomerPortal from './components/CustomerPortal';
import AdminDashboard from './components/AdminDashboard';
import LoginView from './components/LoginView';
import {
  checkHealth,
  getAccountBalance,
  getAccountDeposits,
  getAccountTransactions,
  sendChatMessage,
  getAuditLogs,
  getTelemetryMetrics,
  getDriftStatus,
  retrainModel,
  getAgents,
  quarantineAgent,
  liftQuarantine,
  executeDirectWireTransfer,
  executeDirectLiquidateDeposit,
  resetSystemData,
  getMockAgents,
  subscribeConnectionStatus,
  getSystemStatus,
  getDataSourceMode,
  setDataSourceMode,
  subscribeDataSourceMode,
} from './services/api';
import { CheckCircle2, AlertCircle, Info } from 'lucide-react';


const INITIAL_TRANSACTIONS = [
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
    description: 'Apex Commercial ATM Withdrawal (Indiranagar #04)',
    category: 'Cash',
    amount: 10000.0,
    type: 'debit',
    status: 'Settled',
  },
  {
    id: 'TXN-97940',
    date: '10 Sep 2026',
    description: 'Quarterly Fixed Deposit Interest Settlement',
    category: 'Interest',
    amount: 9062.5,
    type: 'credit',
    status: 'Settled',
  },
];

export default function App() {
  // Session Authentication State: persisted in localStorage so refresh never logs out
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem('apex_auth_session') || sessionStorage.getItem('apex_auth_session');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Backend Health & Connectivity
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [dataSourceMode, setDataSourceModeState] = useState(() => getDataSourceMode());
  const [dockerStatus, setDockerStatus] = useState(null);
  const [latencyMs, setLatencyMs] = useState(0);

  // Customer Banking State
  const [account, setAccount] = useState(() => ({
    account_id: currentUser?.accountId || '401',
    name: currentUser?.name || 'Rahul Sharma',
    balance_inr: currentUser?.accountId === '402' ? 312400.0 : currentUser?.accountId === '403' ? 15000.0 : 84250.0,
    tier: currentUser?.tier || (currentUser?.accountId === '402' ? 'PLATINUM' : currentUser?.accountId === '403' ? 'SILVER' : 'GOLD'),
  }));
  const [deposits, setDeposits] = useState(() => ({
    account_id: currentUser?.accountId || '401',
    total_deposits_inr: 0,
    deposits: [],
  }));
  const [refreshingAssets, setRefreshingAssets] = useState(false);

  // Dynamic Transaction Ledger State with durable per-user localStorage persistence
  const [transactions, setTransactions] = useState(() => {
    const accId = currentUser?.accountId || '401';
    try {
      const saved = localStorage.getItem(`apex_account_transactions_${accId}`);
      return saved ? JSON.parse(saved) : INITIAL_TRANSACTIONS;
    } catch {
      return INITIAL_TRANSACTIONS;
    }
  });

  // Automatically persist transaction changes across page reloads per user
  useEffect(() => {
    const accId = currentUser?.accountId || '401';
    try {
      localStorage.setItem(`apex_account_transactions_${accId}`, JSON.stringify(transactions));
    } catch (e) {
      console.error('Failed to persist transactions in localStorage:', e);
    }
  }, [transactions, currentUser?.accountId]);


  // AI Chat Assistant State
  const [chatMessages, setChatMessages] = useState(() => [
    {
      sender: 'bot',
      text: `Hello ${currentUser?.name || 'Rahul'}! I am your Apex Bank AI Assistant (Agent-Support-${currentUser?.accountId || '401'}). How may I assist you with your accounts or investments today?`,
    },
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [securityBanner, setSecurityBanner] = useState(null);

  // Cyber SOC Admin State
  const [agents, setAgents] = useState(getMockAgents());
  const [auditLogs, setAuditLogs] = useState([]);
  const [filterDecision, setFilterDecision] = useState('ALL');
  const [logsLoading, setLogsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [telemetry, setTelemetry] = useState(null);
  const [driftStatus, setDriftStatus] = useState(null);
  const [retrainLoading, setRetrainLoading] = useState(false);

  // Toast Notification System (Zero Emojis)
  const [toast, setToast] = useState(null);
  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Handle User Login
  const handleLogin = (userSession) => {
    setCurrentUser(userSession);
    try {
      localStorage.setItem('apex_auth_session', JSON.stringify(userSession));
      sessionStorage.setItem('apex_auth_session', JSON.stringify(userSession));
    } catch {
      // storage unavailable
    }
    const accId = userSession?.accountId || '401';
    const userName = userSession?.name || 'Valued Customer';
    const agentName = `Agent-Support-${accId}`;
    setChatMessages([
      {
        sender: 'bot',
        text: `Hello ${userName}! I am your Apex Bank Virtual Assistant (${agentName}). How may I assist you with your accounts or investments today?`,
      },
    ]);
  };

  // Handle User Sign Out
  const handleSignOut = () => {
    setCurrentUser(null);
    try {
      localStorage.removeItem('apex_auth_session');
      sessionStorage.removeItem('apex_auth_session');
    } catch {
      // storage unavailable
    }
  };

  // Subscribe to backend health and system status updates
  useEffect(() => {
    const unsubMode = subscribeDataSourceMode((mode) => {
      setDataSourceModeState(mode);
    });
    const unsubConn = subscribeConnectionStatus((status) => {
      setIsBackendOnline(status);
    });

    const checkSystem = async () => {
      try {
        const sys = await getSystemStatus();
        setIsBackendOnline(sys.backend_connected);
        setDockerStatus(sys.docker_status);
        setLatencyMs(sys.latency_ms);
      } catch {
        setIsBackendOnline(false);
      }
    };

    checkSystem();
    const interval = setInterval(checkSystem, 4000);

    return () => {
      unsubMode();
      unsubConn();
      clearInterval(interval);
    };
  }, []);

  const handleToggleDataSourceMode = (newMode) => {
    setDataSourceMode(newMode);
    setDataSourceModeState(newMode);
    showToast(
      newMode === 'live'
        ? 'Switched to Live Backend Data Mode (FastAPI :8000 & SQLite/Postgres)'
        : 'Switched to Demo Mock Mode (Simulated Sandbox Data)',
      'info'
    );
    loadBankingData();
    loadSocData();
  };

  // Fetch Banking Data
  const loadBankingData = useCallback(async () => {
    setRefreshingAssets(true);
    const targetAcc = currentUser?.accountId || '401';
    try {
      const [bal, dep, serverTxns] = await Promise.all([
        getAccountBalance(targetAcc),
        getAccountDeposits(targetAcc),
        getAccountTransactions(targetAcc),
      ]);
      if (bal) setAccount(bal);
      if (dep) setDeposits(dep);
      if (serverTxns && serverTxns.length > 0) {
        setTransactions(serverTxns);
      }
    } catch (err) {
      console.error('Error loading banking data:', err);
    } finally {
      setRefreshingAssets(false);
    }
  }, [currentUser?.accountId]);


  // Fetch SOC Telemetry & Audit Logs & Agents
  const loadSocData = useCallback(async () => {
    setLogsLoading(true);
    try {
      const [logs, tel, drift, agList] = await Promise.all([
        getAuditLogs(50, null, filterDecision),
        getTelemetryMetrics(),
        getDriftStatus(),
        getAgents(),
      ]);
      if (logs) setAuditLogs(logs);
      if (tel) setTelemetry(tel);
      if (drift) setDriftStatus(drift);
      if (agList) setAgents(agList);
    } catch (err) {
      console.error('Error loading SOC data:', err);
    } finally {
      setLogsLoading(false);
    }
  }, [filterDecision]);

  // Initial load
  useEffect(() => {
    let mounted = true;
    const init = async () => {
      if (mounted) {
        await loadBankingData();
        await loadSocData();
      }
    };
    init();
    return () => {
      mounted = false;
    };
  }, [loadBankingData, loadSocData]);

  // Periodic Auto-refresh for SOC Admin
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadSocData();
      checkHealth().then((h) => setIsBackendOnline(h.online));
    }, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadSocData]);

  // Handle Sending Chat Message
  const handleSendMessage = async (userText) => {
    if (!userText.trim()) return;

    setChatMessages((prev) => [...prev, { sender: 'user', text: userText }]);
    setChatLoading(true);

    const activeAccountId = account?.account_id || currentUser?.accountId || '401';

    try {
      const data = await sendChatMessage(userText, activeAccountId);

      const isBlocked = data.governor_status === 'BLOCKED';
      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: data.reply,
          isBlocked,
          action: data.action_taken,
        },
      ]);

      // Trigger real-time security intercept banner
      if (isBlocked) {
        setSecurityBanner({
          type: 'BLOCK',
          action: data.action_taken || 'Tool Request',
          reason: data.violation_reason || 'SOX-404 Zero-Trust Policy Deny',
          time: new Date().toLocaleTimeString(),
        });
        showToast(`GOVERNOR INTERCEPT: ${data.action_taken || 'Operation'} blocked by policy`, 'error');
      } else {
        setSecurityBanner({
          type: 'ALLOW',
          action: data.action_taken || 'Tool Execution',
          latency: data.pep_latency_ms || 1.15,
          time: new Date().toLocaleTimeString(),
        });
      }

      // Refresh data in background
      loadBankingData();
      loadSocData();
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: 'Security Alert: Failed to negotiate with Governor PEP Gateway.',
          isBlocked: true,
        },
      ]);
      showToast(`Gateway Error: ${err.message}`, 'error');
    } finally {
      setChatLoading(false);
    }
  };

  // Direct Customer Action: Wire Transfer
  const handleExecuteWire = async (transferData) => {
    try {
      const res = await executeDirectWireTransfer(
        transferData.source_account,
        transferData.destination_account,
        transferData.amount_inr,
        transferData.remarks
      );
      const recipientName =
        transferData.destination_account === '401'
          ? 'Rahul Sharma (#401)'
          : transferData.destination_account === '402'
          ? 'Priya Patel (#402)'
          : transferData.destination_account === '403'
          ? 'Vikram Malhotra (#403)'
          : `Beneficiary (#${transferData.destination_account})`;
      const newTxn = {
        id: res?.transaction_id || `TXN-WIRE-${Date.now().toString().slice(-5)}`,
        date: 'Just now',
        description: `Outward Wire Settlement to ${recipientName}`,
        category: 'Wire Transfer',
        amount: parseFloat(transferData.amount_inr),
        type: 'debit',
        status: 'Settled',
      };
      setTransactions((prev) => [newTxn, ...prev]);

      // Immediately synchronize local state so UI updates without waiting for network poll
      if (typeof res?.source_new_balance === 'number') {
        setAccount((prev) => ({ ...prev, balance_inr: res.source_new_balance }));
      } else {
        setAccount((prev) => ({
          ...prev,
          balance_inr: Math.max(0, prev.balance_inr - parseFloat(transferData.amount_inr)),
        }));
      }

      await loadBankingData();
      await loadSocData();
      showToast(`Wire transfer of ₹${parseFloat(transferData.amount_inr).toLocaleString('en-IN')} completed.`, 'success');
      return res;
    } catch (err) {
      showToast(`Wire transfer failed: ${err.message}`, 'error');
      throw err;
    }
  };

  // Direct Customer Action: Liquidate FD
  const handleExecuteLiquidate = async (accountId, depositId) => {
    try {
      const res = await executeDirectLiquidateDeposit(accountId, depositId);
      const liqAmount = res?.liquidated_amount_inr || 500000.0;
      const newTxn = {
        id: `TXN-LIQ-${Date.now().toString().slice(-5)}`,
        date: 'Just now',
        description: `Fixed Deposit Premature Liquidation (${depositId})`,
        category: 'Investment Credit',
        amount: liqAmount,
        type: 'credit',
        status: 'Settled',
      };
      setTransactions((prev) => [newTxn, ...prev]);

      // Immediately synchronize local state with credited proceeds
      if (typeof res?.new_balance_inr === 'number') {
        setAccount((prev) => ({ ...prev, balance_inr: res.new_balance_inr }));
      } else {
        setAccount((prev) => ({ ...prev, balance_inr: prev.balance_inr + liqAmount }));
      }
      setDeposits((prev) => ({
        ...prev,
        total_deposits_inr: Math.max(0, (prev.total_deposits_inr || 0) - liqAmount),
        deposits: (prev.deposits || []).map((d) =>
          d.deposit_id === depositId ? { ...d, status: 'LIQUIDATED' } : d
        ),
      }));

      await loadBankingData();
      await loadSocData();
      showToast('Fixed Deposit successfully liquidated into Primary Savings.', 'success');
      return res;
    } catch (err) {
      showToast(`Liquidation failed: ${err.message}`, 'error');
      throw err;
    }
  };

  // Admin Action: Emergency Kill-Switch Quarantine
  const handleQuarantineAgent = async (agentId) => {
    try {
      await quarantineAgent(agentId, 'SOC Emergency Kill-Switch Activated');
      setAgents((prev) =>
        prev.map((a) => (a.agent_id === agentId ? { ...a, status: 'QUARANTINED' } : a))
      );
      loadSocData();
      showToast(`Agent ${agentId} QUARANTINED! Cryptographic passport revoked.`, 'error');
    } catch (err) {
      showToast(`Failed to quarantine agent: ${err.message}`, 'error');
    }
  };

  // Admin Action: FFIEC Reinstatement
  const handleLiftQuarantine = async (agentId, justification, analystId) => {
    try {
      await liftQuarantine(agentId, justification, analystId);
      setAgents((prev) =>
        prev.map((a) => (a.agent_id === agentId ? { ...a, status: 'ACTIVE' } : a))
      );
      loadSocData();
      showToast(`Agent ${agentId} Reinstated under FFIEC protocol by ${analystId}`, 'success');
    } catch (err) {
      showToast(`Failed to reinstate agent: ${err.message}`, 'error');
    }
  };

  // Admin Action: Retrain Isolation Forest
  const handleRetrainModel = async () => {
    setRetrainLoading(true);
    try {
      const res = await retrainModel();
      loadSocData();
      showToast('Isolation Forest retrained successfully with buffered RLHF feedback.', 'success');
      return res;
    } catch (err) {
      showToast(`Retraining failed: ${err.message}`, 'error');
      throw err;
    } finally {
      setRetrainLoading(false);
    }
  };

  // Admin Action: Reset System Values
  const [resetLoading, setResetLoading] = useState(false);
  const handleResetSystemValues = async () => {
    setResetLoading(true);
    try {
      await resetSystemData();
      setAccount({
        account_id: '401',
        name: 'Rahul Sharma',
        balance_inr: 84250.0,
        tier: 'GOLD',
      });
      setDeposits({
        account_id: '401',
        total_deposits_inr: 500000.0,
        deposits: [
          {
            deposit_id: 'FD-901',
            type: 'Cumulative Fixed Deposit',
            principal_inr: 500000.0,
            interest_rate: '7.25%',
            maturity_date: '2027-03-31',
            status: 'LOCKED',
          },
        ],
      });
      setTransactions(INITIAL_TRANSACTIONS);
      try {
        localStorage.removeItem('apex_account_transactions_401');
      } catch {
        // storage ignored
      }
      await loadBankingData();
      await loadSocData();
      showToast('System reset complete: All accounts, deposits, transactions, and ML metrics restored to baseline.', 'success');
    } catch (err) {
      showToast(`Reset failed: ${err.message}`, 'error');
    } finally {
      setResetLoading(false);
    }
  };

  const quarantinedCount = agents.filter((a) => a.status === 'QUARANTINED').length;
  // Role-based Partition: strictly determined by authenticated user role (No manual switching on home page)
  const effectiveMode = currentUser?.role === 'admin' ? 'admin' : 'customer';

  // Unauthenticated View: Render Corporate Login Screen
  if (!currentUser) {
    return <LoginView onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-indigo-600 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        isBackendOnline={isBackendOnline}
        user={currentUser}
        onSignOut={handleSignOut}
        fleetStatus={{ total: agents.length, quarantined: quarantinedCount }}
        dockerStatus={dockerStatus}
        dataSourceMode={dataSourceMode}
        onToggleDataSourceMode={handleToggleDataSourceMode}
        latencyMs={latencyMs}
      />

      {/* Toast Notification Alert (Zero Emojis) */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-fadeIn">
          <div
            className={`px-4 py-3 rounded-xl border shadow-2xl flex items-center gap-3 text-xs font-semibold ${
              toast.type === 'error'
                ? 'bg-rose-950/95 border-rose-600/70 text-rose-200'
                : toast.type === 'success'
                ? 'bg-emerald-950/95 border-emerald-600/70 text-emerald-200'
                : 'bg-slate-900/95 border-slate-700 text-slate-200'
            }`}
          >
            {toast.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : toast.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-blue-400 shrink-0" />
            )}
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {/* Main Role-Based View Container (Strict Role Partition) */}
      <main className="flex-1">
        {effectiveMode === 'admin' ? (
          <AdminDashboard
            telemetry={telemetry}
            driftStatus={driftStatus}
            agents={agents}
            auditLogs={auditLogs}
            filterDecision={filterDecision}
            setFilterDecision={setFilterDecision}
            onRefreshLogs={loadSocData}
            autoRefresh={autoRefresh}
            setAutoRefresh={setAutoRefresh}
            logsLoading={logsLoading}
            onQuarantineAgent={handleQuarantineAgent}
            onLiftQuarantine={handleLiftQuarantine}
            onRetrainModel={handleRetrainModel}
            retrainLoading={retrainLoading}
            isBackendOnline={isBackendOnline}
            onResetSystemValues={handleResetSystemValues}
            resetLoading={resetLoading}
            dockerStatus={dockerStatus}
            dataSourceMode={dataSourceMode}
            onToggleDataSourceMode={handleToggleDataSourceMode}
            latencyMs={latencyMs}
          />

        ) : (
          <CustomerPortal
            account={account}
            deposits={deposits}
            transactions={transactions}
            agents={agents}
            onRefreshAssets={loadBankingData}
            refreshing={refreshingAssets}
            chatMessages={chatMessages}
            onSendMessage={handleSendMessage}
            chatLoading={chatLoading}
            securityBanner={securityBanner}
            onExecuteWire={handleExecuteWire}
            onExecuteLiquidate={handleExecuteLiquidate}
          />
        )}
      </main>

      {/* Enterprise Institutional Footer */}
      <footer className="border-t border-zinc-800/80 bg-zinc-950 px-4 sm:px-8 py-5 text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-zinc-400">APEX COMMERCIAL BANK</span>
            <span>•</span>
            <span>Zero-Trust Identity & Access Governor (BFSI Non-Human Identities)</span>
          </div>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <span>FastAPI PEP :8000</span>
            <span>•</span>
            <span>SOX-404 / FFIEC Cat-3 Compliant</span>
            <span>•</span>
            <span>Deloitte Capstone 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}