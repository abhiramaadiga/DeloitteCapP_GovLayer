import React, { useState, useEffect, useMemo } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Plus,
  RotateCcw,
  RefreshCw,
  Search,
  Trash2,
  Edit3,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  Zap,
  X,
  Loader2,
  Check
} from 'lucide-react';
import {
  getGovernancePolicies,
  createGovernancePolicy,
  updateGovernancePolicy,
  deleteGovernancePolicy,
  resetGovernancePolicies,
  getAvailableBankingTools
} from '../../services/api';

export default function PolicyManagementSection({ isBackendOnline = true }) {
  const [policies, setPolicies] = useState([]);
  const [tools, setTools] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [successNotice, setSuccessNotice] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [actionFilter, setActionFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // UI Panels
  const [toolsDrawerOpen, setToolsDrawerOpen] = useState(true);

  // Modals
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' | 'edit'
  const [activePolicy, setActivePolicy] = useState(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [policyToDelete, setPolicyToDelete] = useState(null);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Form State
  const initialForm = {
    policy_id: '',
    agent_id: '*',
    role: 'tier1_customer_service',
    endpoint_pattern: '',
    method: 'GET',
    action: 'DENY',
    compliance_tag: 'SOX-404',
    description: '',
    is_active: true
  };
  const [formData, setFormData] = useState(initialForm);

  const fetchAll = async () => {
    try {
      setError(null);
      const [polData, toolsData] = await Promise.all([
        getGovernancePolicies(),
        getAvailableBankingTools()
      ]);
      setPolicies(polData.policies || []);
      setStats(polData.stats || null);
      setTools(toolsData || []);
    } catch (err) {
      console.error('Failed to load governance policies:', err);
      setError(err.message || 'Failed to load policies.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAll();
  };

  const showSuccess = (msg) => {
    setSuccessNotice(msg);
    setTimeout(() => setSuccessNotice(null), 4000);
  };

  // Toggle Policy is_active (Instant Live Enforcement)
  const handleToggleActive = async (policy) => {
    const updatedStatus = !policy.is_active;
    // Optimistic UI update
    setPolicies((prev) =>
      prev.map((p) => (p.policy_id === policy.policy_id ? { ...p, is_active: updatedStatus } : p))
    );

    try {
      await updateGovernancePolicy(policy.policy_id, { is_active: updatedStatus });
      showSuccess(
        `Policy ${policy.policy_id} is now ${updatedStatus ? 'ACTIVE (Enforced)' : 'INACTIVE (Bypassed)'}. Cache synchronized in <0.05ms.`
      );
      const polData = await getGovernancePolicies();
      setStats(polData.stats || null);
    } catch (err) {
      // Rollback on error
      setPolicies((prev) =>
        prev.map((p) => (p.policy_id === policy.policy_id ? { ...p, is_active: policy.is_active } : p))
      );
      setError(`Failed to toggle policy: ${err.message}`);
    }
  };

  // Open Create Modal (optionally pre-filled from tool)
  const handleOpenCreate = (prefill = null) => {
    setModalMode('create');
    if (prefill) {
      setFormData({
        policy_id: `POL-CUSTOM-${Math.floor(1000 + Math.random() * 9000)}`,
        agent_id: '*',
        role: prefill.default_roles?.[0] || 'tier1_customer_service',
        endpoint_pattern: prefill.pattern || prefill.endpoint || '',
        method: prefill.method || 'GET',
        action: 'DENY',
        compliance_tag: prefill.risk_level === 'CRITICAL' ? 'PCI-DSS' : 'SOX-404',
        description: `Enforce access governance for ${prefill.name || 'banking endpoint'}.`,
        is_active: true
      });
    } else {
      setFormData({
        ...initialForm,
        policy_id: `POL-CUSTOM-${Math.floor(1000 + Math.random() * 9000)}`
      });
    }
    setModalOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (policy) => {
    setModalMode('edit');
    setActivePolicy(policy);
    setFormData({
      policy_id: policy.policy_id,
      agent_id: policy.agent_id || '*',
      role: policy.role || '*',
      endpoint_pattern: policy.endpoint_pattern || '',
      method: policy.method || '*',
      action: policy.action || 'DENY',
      compliance_tag: policy.compliance_tag || 'SOX-404',
      description: policy.description || '',
      is_active: policy.is_active
    });
    setModalOpen(true);
  };

  // Save Modal Form (Create or Edit)
  const handleSubmitForm = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    try {
      if (modalMode === 'create') {
        const res = await createGovernancePolicy(formData);
        const newPolicy = res?.policy || { ...formData, id: Date.now() };
        // Instantly prepend to state so the table and all 4 metric cards update immediately
        setPolicies((prev) => [newPolicy, ...prev.filter((p) => p.policy_id !== newPolicy.policy_id)]);
        showSuccess(`Policy ${formData.policy_id} created and committed to PostgreSQL. PEP cache synchronized.`);
      } else {
        const res = await updateGovernancePolicy(formData.policy_id, formData);
        const updatedPolicy = res?.policy || formData;
        setPolicies((prev) => prev.map((p) => (p.policy_id === updatedPolicy.policy_id ? updatedPolicy : p)));
        showSuccess(`Policy ${formData.policy_id} updated successfully. PEP cache synchronized.`);
      }
      setModalOpen(false);
      await fetchAll();
    } catch (err) {
      setError(err.message || 'Failed to save policy.');
    } finally {
      setActionLoading(false);
    }
  };

  // Delete Policy
  const handleConfirmDelete = async () => {
    if (!policyToDelete) return;
    setActionLoading(true);
    try {
      await deleteGovernancePolicy(policyToDelete.policy_id);
      setPolicies((prev) => prev.filter((p) => p.policy_id !== policyToDelete.policy_id));
      showSuccess(`Policy ${policyToDelete.policy_id} permanently removed.`);
      setDeleteModalOpen(false);
      setPolicyToDelete(null);
      await fetchAll();
    } catch (err) {
      setError(`Failed to delete policy: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Reset to Baseline Policies
  const handleConfirmReset = async () => {
    setActionLoading(true);
    try {
      await resetGovernancePolicies();
      showSuccess('Governance policies successfully restored to initial baseline rules.');
      setResetModalOpen(false);
      await fetchAll();
    } catch (err) {
      setError(`Failed to reset policies: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Filtered Policies
  const filteredPolicies = useMemo(() => {
    return policies.filter((p) => {
      // Search
      if (search.trim()) {
        const q = search.toLowerCase();
        const matches =
          p.policy_id?.toLowerCase().includes(q) ||
          p.endpoint_pattern?.toLowerCase().includes(q) ||
          p.role?.toLowerCase().includes(q) ||
          p.compliance_tag?.toLowerCase().includes(q) ||
          p.description?.toLowerCase().includes(q);
        if (!matches) return false;
      }
      // Role
      if (roleFilter !== 'ALL' && p.role !== roleFilter && p.role !== '*') {
        return false;
      }
      // Action
      if (actionFilter !== 'ALL' && p.action !== actionFilter) {
        return false;
      }
      // Status
      if (statusFilter === 'ACTIVE' && !p.is_active) return false;
      if (statusFilter === 'INACTIVE' && p.is_active) return false;

      return true;
    });
  }, [policies, search, roleFilter, actionFilter, statusFilter]);

  const activeCount = policies.filter((p) => p.is_active).length;
  const denyCount = policies.filter((p) => p.is_active && p.action === 'DENY').length;
  const allowCount = policies.filter((p) => p.is_active && p.action === 'ALLOW').length;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Notification Banner */}
      {successNotice && (
        <div className="bg-emerald-950/80 border border-emerald-500/60 rounded-xl px-4 py-3 text-xs text-emerald-200 flex items-center justify-between shadow-lg shadow-emerald-950/30 animate-slide-up">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessNotice(null)}
            className="p-1 hover:bg-emerald-900/50 rounded text-emerald-400"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {error && (
        <div className="bg-rose-950/80 border border-rose-500/60 rounded-xl px-4 py-3 text-xs text-rose-200 flex items-center justify-between shadow-lg shadow-rose-950/30 animate-slide-up">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="p-1 hover:bg-rose-900/50 rounded text-rose-400"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Header Card & Architecture Badges */}
      <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-6 shadow-xl backdrop-blur">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="text-xs uppercase font-mono font-bold tracking-widest text-indigo-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" />
                Policy Enforcement Point (PEP)
              </span>
              <span className="text-[10px] bg-indigo-950/90 text-indigo-300 border border-indigo-800/80 px-2 py-0.5 rounded-full font-mono">
                Dual-Plane Architecture
              </span>
              <span className="text-[10px] bg-emerald-950/90 text-emerald-300 border border-emerald-800/80 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
                <Zap className="w-3 h-3 text-emerald-400" />
                In-Memory Cache &lt;0.05ms
              </span>
              <span className="text-[10px] bg-blue-950/90 text-blue-300 border border-blue-800/80 px-2 py-0.5 rounded-full font-mono">
                PostgreSQL Source of Truth
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Dynamic Policy Governance &amp; Rule Engine</span>
            </h2>
            <p className="text-xs text-zinc-400 mt-1 max-w-3xl leading-relaxed">
              Define deterministic Zero-Trust access control lists, least-privilege boundaries, and SOX-404 banking compliance rules.
              Modifications trigger instant atomic cache invalidation and apply live to all governed agent tool executions with zero server downtime.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-2.5 rounded-xl bg-zinc-850 hover:bg-zinc-800 border border-zinc-700/80 text-zinc-300 hover:text-white transition disabled:opacity-50"
              title="Refresh Policies"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-indigo-400' : ''}`} />
            </button>

            <button
              type="button"
              onClick={() => setResetModalOpen(true)}
              className="px-3.5 py-2.5 rounded-xl bg-zinc-850 hover:bg-zinc-800 border border-zinc-700/80 hover:border-amber-600/70 text-zinc-300 hover:text-amber-300 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
              <span>Reset Baseline</span>
            </button>

            <button
              type="button"
              onClick={() => handleOpenCreate()}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-indigo-950/50 transition hover-lift"
            >
              <Plus className="w-4 h-4" />
              <span>Create Policy</span>
            </button>
          </div>
        </div>

        {/* 4 Summary Metric Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-zinc-800/80">
          <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60">
            <div className="text-[11px] text-zinc-400 font-medium">Total Governed Policies</div>
            <div className="text-xl font-bold font-mono text-white mt-1">{policies.length}</div>
            <div className="text-[10px] text-zinc-500 font-mono mt-0.5">PostgreSQL Table Rows</div>
          </div>

          <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60">
            <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Active Enforced
            </div>
            <div className="text-xl font-bold font-mono text-emerald-300 mt-1">{activeCount}</div>
            <div className="text-[10px] text-zinc-500 font-mono mt-0.5">L1 In-Memory Cache</div>
          </div>

          <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60">
            <div className="text-[11px] text-rose-400 font-medium flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              Hard Denials
            </div>
            <div className="text-xl font-bold font-mono text-rose-300 mt-1">{denyCount}</div>
            <div className="text-[10px] text-zinc-500 font-mono mt-0.5">SOX-404 / PCI-DSS Prohibitions</div>
          </div>

          <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60">
            <div className="text-[11px] text-indigo-400 font-medium flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              Explicit Authorizations
            </div>
            <div className="text-xl font-bold font-mono text-indigo-300 mt-1">{allowCount}</div>
            <div className="text-[10px] text-zinc-500 font-mono mt-0.5">Least-Privilege Passports</div>
          </div>
        </div>
      </div>

      {/* Available Banking Tools & Endpoints Reference Drawer */}
      <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 shadow-xl overflow-hidden backdrop-blur">
        <button
          type="button"
          onClick={() => setToolsDrawerOpen(!toolsDrawerOpen)}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-zinc-850/40 transition"
        >
          <div className="flex items-center gap-2.5">
            <Layers className="w-4 h-4 text-indigo-400" />
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Available Governed Banking Tools &amp; Options</span>
                <span className="text-[10px] bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded-full font-mono">
                  {tools.length} Registered Endpoints
                </span>
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Inspect registered upstream banking endpoints and quickly configure enforcement rules.
              </p>
            </div>
          </div>
          <div className="p-1 rounded-lg bg-zinc-800 text-zinc-400">
            {toolsDrawerOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </button>

        {toolsDrawerOpen && (
          <div className="p-6 pt-2 border-t border-zinc-800/80 animate-slide-up">
            <div className="max-h-80 overflow-y-auto pr-1.5 custom-scrollbar">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {tools.map((t) => {
                const isCritical = t.risk_level === 'CRITICAL';
                const isHigh = t.risk_level === 'HIGH';
                const isMed = t.risk_level === 'MEDIUM';

                return (
                  <div
                    key={t.tool_id}
                    className="p-3.5 bg-zinc-950/70 border border-zinc-800/80 rounded-xl hover:border-zinc-700 transition flex flex-col justify-between group"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-1.5 mb-2">
                        <span
                          className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                            t.method === 'POST'
                              ? 'bg-amber-950/90 text-amber-300 border border-amber-800/80'
                              : 'bg-sky-950/90 text-sky-300 border border-sky-800/80'
                          }`}
                        >
                          {t.method}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                            isCritical
                              ? 'bg-rose-950/80 text-rose-300 border border-rose-800/80'
                              : isHigh
                              ? 'bg-orange-950/80 text-orange-300 border border-orange-800/80'
                              : isMed
                              ? 'bg-amber-950/80 text-amber-300 border border-amber-800/80'
                              : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/80'
                          }`}
                        >
                          {t.risk_level}
                        </span>
                      </div>

                      <div className="font-semibold text-xs text-white truncate" title={t.name}>
                        {t.name}
                      </div>

                      <div className="text-[11px] font-mono text-zinc-400 mt-1 bg-zinc-900/90 px-2 py-1 rounded border border-zinc-800/90 truncate" title={t.pattern}>
                        {t.pattern}
                      </div>

                      <p className="text-[11px] text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
                        {t.description}
                      </p>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-zinc-900 flex items-center justify-between">
                      <span className="text-[10px] text-zinc-500 font-mono truncate max-w-[120px]" title={t.default_roles?.join(', ')}>
                        {t.default_roles?.join(', ')}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleOpenCreate(t)}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 group-hover:underline"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Enforce Rule</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Policies Table Section */}
      <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 shadow-xl overflow-hidden backdrop-blur">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-zinc-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 w-full md:w-auto flex-1">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search policy ID, pattern, role, tag..."
                className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-zinc-950 border border-zinc-700/80 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            {/* Role Filter */}
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-xl bg-zinc-950 border border-zinc-700/80 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Roles</option>
              <option value="tier1_customer_service">tier1_customer_service</option>
              <option value="payment_executor">payment_executor</option>
              <option value="branch_officer">branch_officer</option>
              <option value="compliance_auditor">compliance_auditor</option>
              <option value="*">* (Wildcard Any Role)</option>
            </select>

            {/* Action Filter */}
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-xl bg-zinc-950 border border-zinc-700/80 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Actions</option>
              <option value="DENY">DENY (Prohibition)</option>
              <option value="ALLOW">ALLOW (Authorization)</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-xl bg-zinc-950 border border-zinc-700/80 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Status</option>
              <option value="ACTIVE">Active Enforced</option>
              <option value="INACTIVE">Inactive Bypassed</option>
            </select>
          </div>

          <div className="text-xs text-zinc-500 font-mono shrink-0">
            Showing {filteredPolicies.length} of {policies.length} policies
          </div>
        </div>

        {/* Data Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-zinc-950/80 text-zinc-400 font-mono uppercase tracking-wider text-[11px] border-b border-zinc-800">
                <th className="px-4 py-3">Policy ID &amp; Tag</th>
                <th className="px-4 py-3">Governed Entity</th>
                <th className="px-4 py-3">Target Endpoint &amp; Method</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Security Rationale / Description</th>
                <th className="px-4 py-3 text-center">Live Enforcement</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-zinc-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                    <span>Loading Zero-Trust governance policies from PostgreSQL...</span>
                  </td>
                </tr>
              ) : filteredPolicies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-zinc-500">
                    No matching policies found. Adjust search filters or create a new policy.
                  </td>
                </tr>
              ) : (
                filteredPolicies.map((p) => {
                  const isDeny = p.action === 'DENY';
                  const isActive = p.is_active;

                  return (
                    <tr
                      key={p.id || p.policy_id}
                      className={`hover:bg-zinc-850/50 transition ${
                        !isActive ? 'opacity-60 bg-zinc-950/30' : ''
                      }`}
                    >
                      {/* Policy ID & Compliance Tag */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="font-bold text-white text-xs">{p.policy_id}</div>
                        <div className="mt-1">
                          <span className="text-[10px] bg-indigo-950/90 text-indigo-300 border border-indigo-800/80 px-2 py-0.5 rounded-full font-mono">
                            {p.compliance_tag || 'SOX-404'}
                          </span>
                        </div>
                      </td>

                      {/* Governed Entity (Role & Agent) */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="text-zinc-200 text-xs">
                          {p.role === '*' ? (
                            <span className="text-zinc-400 italic">* (Any Governed Role)</span>
                          ) : (
                            <span className="bg-zinc-800/90 px-1.5 py-0.5 rounded border border-zinc-700/80 text-zinc-300">
                              {p.role}
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-zinc-500 mt-1">
                          Agent ID: {p.agent_id}
                        </div>
                      </td>

                      {/* Target Endpoint & Method */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              p.method === 'POST'
                                ? 'bg-amber-950/90 text-amber-300 border border-amber-800/80'
                                : p.method === 'GET'
                                ? 'bg-sky-950/90 text-sky-300 border border-sky-800/80'
                                : 'bg-zinc-800 text-zinc-300'
                            }`}
                          >
                            {p.method}
                          </span>
                          <span className="text-zinc-300 text-xs font-mono font-semibold">
                            {p.endpoint_pattern}
                          </span>
                        </div>
                      </td>

                      {/* Action (DENY / ALLOW) */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        {isDeny ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-950/90 text-rose-300 border border-rose-800/80">
                            <ShieldAlert className="w-3 h-3 text-rose-400" />
                            <span>DENY</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950/90 text-emerald-300 border border-emerald-800/80">
                            <ShieldCheck className="w-3 h-3 text-emerald-400" />
                            <span>ALLOW</span>
                          </span>
                        )}
                      </td>

                      {/* Description */}
                      <td className="px-4 py-3 font-sans text-xs text-zinc-300 max-w-xs truncate" title={p.description}>
                        {p.description}
                      </td>

                      {/* Live Enforcement Toggle Switch */}
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleActive(p)}
                          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                            isActive ? 'bg-emerald-600' : 'bg-zinc-800'
                          }`}
                          title={`Click to ${isActive ? 'Deactivate (Bypass)' : 'Activate (Enforce)'}`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                              isActive ? 'translate-x-5' : 'translate-x-0'
                            }`}
                          />
                        </button>
                        <div className="text-[10px] font-mono mt-1 font-semibold">
                          {isActive ? (
                            <span className="text-emerald-400 flex items-center justify-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              ACTIVE
                            </span>
                          ) : (
                            <span className="text-zinc-500">INACTIVE</span>
                          )}
                        </div>
                      </td>

                      {/* Action Buttons */}
                      <td className="px-4 py-3 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(p)}
                            className="p-1.5 rounded-lg bg-zinc-850 hover:bg-zinc-700 text-zinc-300 hover:text-white transition"
                            title="Edit Policy"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setPolicyToDelete(p);
                              setDeleteModalOpen(true);
                            }}
                            className="p-1.5 rounded-lg bg-zinc-850 hover:bg-rose-950 text-zinc-300 hover:text-rose-400 border border-transparent hover:border-rose-800/80 transition"
                            title="Delete Policy"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Testing Guide Card */}
      <div className="bg-zinc-950/80 rounded-2xl border border-zinc-800/90 p-5 shadow-lg">
        <div className="flex items-start gap-3">
          <Zap className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Live Interactive Verification Guide
            </h4>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Every toggle or update to this table commits to PostgreSQL and atomically synchronizes the in-memory PEP cache in &lt;0.05ms:
            </p>
            <ul className="text-xs text-zinc-300 space-y-1 pt-1 font-mono">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                <span><strong>Test 1:</strong> Toggle <code className="text-indigo-300">POL-SOX-404</code> to INACTIVE. Open customer chatbot and request: <em>&quot;Transfer ₹50,000 to account 402&quot;</em>. Watch the Governor allow it immediately!</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                <span><strong>Test 2:</strong> Turn <code className="text-indigo-300">POL-SOX-404</code> back to ACTIVE. Retry the transfer in chat — it will be instantaneously blocked by SOX-404.</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span><strong>Test 3:</strong> Click <em>&quot;Enforce Rule&quot;</em> on Balance Inquiry above, set Action to <strong>DENY</strong>. The chatbot will immediately block balance inquiries.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Create / Edit Policy Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 card-hover popup-scale">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Sliders className="w-5 h-5 text-indigo-400" />
                <span>{modalMode === 'create' ? 'Create Governance Policy' : `Edit Policy: ${formData.policy_id}`}</span>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitForm} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-400 font-medium mb-1">Policy ID</label>
                  <input
                    type="text"
                    required
                    disabled={modalMode === 'edit'}
                    value={formData.policy_id}
                    onChange={(e) => setFormData({ ...formData, policy_id: e.target.value })}
                    placeholder="POL-SOX-404"
                    className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-mono disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-zinc-400 font-medium mb-1">Compliance Tag</label>
                  <select
                    value={formData.compliance_tag}
                    onChange={(e) => setFormData({ ...formData, compliance_tag: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-mono"
                  >
                    <option value="SOX-404">SOX-404</option>
                    <option value="BANKING-GOV">BANKING-GOV</option>
                    <option value="PCI-DSS">PCI-DSS</option>
                    <option value="LEAST-PRIVILEGE">LEAST-PRIVILEGE</option>
                    <option value="DUAL-AUTH">DUAL-AUTH</option>
                    <option value="TREASURY-EXEC">TREASURY-EXEC</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-400 font-medium mb-1">Governed Agent Role</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-mono"
                  >
                    <option value="*">* (All Governed Roles)</option>
                    <option value="tier1_customer_service">tier1_customer_service</option>
                    <option value="payment_executor">payment_executor</option>
                    <option value="branch_officer">branch_officer</option>
                    <option value="compliance_auditor">compliance_auditor</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-400 font-medium mb-1">Specific Agent ID</label>
                  <select
                    value={formData.agent_id}
                    onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-mono"
                  >
                    <option value="*">* (Any Fleet Agent)</option>
                    <option value="Agent-Support-01">Agent-Support-01</option>
                    <option value="Agent-Treasury-01">Agent-Treasury-01</option>
                    <option value="Agent-Branch-Manager-01">Agent-Branch-Manager-01</option>
                    <option value="Agent-Audit-01">Agent-Audit-01</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-zinc-400 font-medium mb-1">Target Endpoint Pattern</label>
                  <input
                    type="text"
                    required
                    value={formData.endpoint_pattern}
                    onChange={(e) => setFormData({ ...formData, endpoint_pattern: e.target.value })}
                    placeholder="/transfers/* or /accounts/*/balance"
                    className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-zinc-400 font-medium mb-1">HTTP Method</label>
                  <select
                    value={formData.method}
                    onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-mono"
                  >
                    <option value="*">* (Any Method)</option>
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 items-center">
                <div>
                  <label className="block text-zinc-400 font-medium mb-1">Enforcement Action</label>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="action"
                        value="DENY"
                        checked={formData.action === 'DENY'}
                        onChange={() => setFormData({ ...formData, action: 'DENY' })}
                        className="text-rose-500 focus:ring-rose-500"
                      />
                      <span className="text-rose-300 font-bold font-mono">DENY</span>
                    </label>

                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="radio"
                        name="action"
                        value="ALLOW"
                        checked={formData.action === 'ALLOW'}
                        onChange={() => setFormData({ ...formData, action: 'ALLOW' })}
                        className="text-emerald-500 focus:ring-emerald-500"
                      />
                      <span className="text-emerald-300 font-bold font-mono">ALLOW</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-zinc-400 font-medium mb-1">Status</label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      className="rounded text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-zinc-300 font-mono">Active Immediately</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-zinc-400 font-medium mb-1">Policy Description &amp; Security Rationale</label>
                <textarea
                  rows={2}
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Explain why this policy is enforced under SOX-404 or Zero-Trust governance..."
                  className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-700/80 text-zinc-200 font-sans focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold flex items-center gap-2 shadow-lg shadow-indigo-950/50 transition hover-lift disabled:opacity-50"
                >
                  {actionLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving Policy...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>{modalMode === 'create' ? 'Create & Enforce' : 'Update Policy'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && policyToDelete && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 card-hover popup-scale">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2 text-rose-400 font-bold text-base">
                <Trash2 className="w-5 h-5" />
                <span>Delete Governance Policy</span>
              </div>
              <button
                type="button"
                onClick={() => setDeleteModalOpen(false)}
                className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Are you sure you want to permanently delete policy <strong className="font-mono text-white">{policyToDelete.policy_id}</strong>?
            </p>
            <div className="p-3 bg-zinc-950/80 rounded-xl border border-zinc-800/80 text-xs font-mono space-y-1 text-zinc-400">
              <div>Pattern: <span className="text-zinc-200">{policyToDelete.endpoint_pattern}</span></div>
              <div>Role: <span className="text-zinc-200">{policyToDelete.role}</span></div>
              <div>Action: <span className={policyToDelete.action === 'DENY' ? 'text-rose-400' : 'text-emerald-400'}>{policyToDelete.action}</span></div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeleteModalOpen(false)}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-rose-950/50 transition hover-lift disabled:opacity-50"
              >
                {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                <span>Confirm Delete</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Modal */}
      {resetModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 card-hover popup-scale">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2 text-amber-400 font-bold text-base">
                <RotateCcw className="w-5 h-5" />
                <span>Reset to Baseline Policies</span>
              </div>
              <button
                type="button"
                onClick={() => setResetModalOpen(false)}
                className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              This will restore the 8 baseline Zero-Trust and SOX-404 governance policies in PostgreSQL and reload the in-memory PEP cache. Custom rules will be reset.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setResetModalOpen(false)}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmReset}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-amber-950/50 transition hover-lift disabled:opacity-50"
              >
                {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                <span>Confirm Reset</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
