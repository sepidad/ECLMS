import React, { useState, useEffect } from 'react';
import { 
  Shield, FileText, GitBranch, Users, CheckCircle2, XCircle, 
  RefreshCw, LogOut, AlertCircle, Plus, UserPlus, Bell, Webhook, Activity,
  BarChart3, Search, AlertTriangle, FileSearch, Brain, Wallet, ClipboardCheck, Settings, Mail, MessageSquare, Download, Upload, Plug, LayoutDashboard
} from 'lucide-react';
import FinancesTab from './components/FinancesTab';
import ObligationsTab from './components/ObligationsTab';
import ContractPanel from './components/ContractPanel';
import SettingsModal from './components/SettingsModal';
import SystemHealthTab from './components/SystemHealthTab';
import DataImportTab from './components/DataImportTab';
import IntegrationsTab from './components/IntegrationsTab';
import DashboardTab from './components/DashboardTab';
import GuaranteesTab from './components/GuaranteesTab';
import ApprovalInbox from './components/ApprovalInbox';
import AdminCenterTab from './components/AdminCenterTab';
import { downloadAuthenticated } from './download';

interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  organization_id: string;
  roles?: string[];
}

interface AuditItem {
  id: string;
  event_type: string;
  source_module: string;
  actor_id?: string;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
}

interface NotificationItem {
  id: string;
  subject: string;
  body: string;
  channel: string;
  is_read: boolean;
  created_at?: string;
}

interface WebhookSub {
  id: string;
  url: string;
  event_type: string;
  is_active?: boolean;
}

interface Contract {
  id: string;
  title: string;
  reference_number: string;
  counterparty: string;
  state: string;
  owner_id: string;
  organization_id: string;
  current_version_id?: string;
  created_at?: string;
}

interface WorkflowStep {
  name: string;
  assigned_role: string;
  status: string;
  parallel_group_id?: string;
  delegated_to?: string;
  escalated_at?: string;
  decided_by?: string;
  comment?: string;
}

interface Workflow {
  id: string;
  contract_id: string;
  definition_id: string;
  status: string;
  current_step_number?: number;
  current_step?: string;
  current_step_role?: string;
  steps: WorkflowStep[];
}

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('eclms_token'));
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'contracts' | 'approvals' | 'workflows' | 'users' | 'admin' | 'notifications' | 'audit' | 'reporting' | 'intelligence' | 'finances' | 'obligations' | 'guarantees' | 'imports' | 'integrations' | 'system'>('dashboard');
  
  // Auth state
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [loginError, setLoginError] = useState('');

  // Data state
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<Record<string, Workflow>>({});
  const [users, setUsers] = useState<User[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookSub[]>([]);
  const [webhookDeliveries, setWebhookDeliveries] = useState<Record<string, any>>({});
  const [emailDeliveries, setEmailDeliveries] = useState<any>(null);
  const [smsDeliveries, setSmsDeliveries] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [reporting, setReporting] = useState<any>(null);
  const [riskOverview, setRiskOverview] = useState<any>(null);
  const [contractRisk, setContractRisk] = useState<any>(null);
  const [clauseAnalysis, setClauseAnalysis] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [riskLoading, setRiskLoading] = useState(false);
  
  // Selected Contract & Workflow
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [workflowHistory, setWorkflowHistory] = useState<any[]>([]);

  // Forms
  const [newTitle, setNewTitle] = useState('');
  const [newRef, setNewRef] = useState('');
  const [newCounterparty, setNewCounterparty] = useState('');
  const [newDefId, setNewDefId] = useState('contract-approval');
  
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPassword, setNewPassword] = useState('password123');
  const [newRole, setNewRole] = useState('CONTRACT_MANAGER');

  const [transitionComment, setTransitionComment] = useState('');
  const [transitionStepName, setTransitionStepName] = useState('');
  const [pauseReason, setPauseReason] = useState('');
  const [delegateToUser, setDelegateToUser] = useState('');
  const [escalateRole, setEscalateRole] = useState('ADMIN');

  const [selectedContractId, setSelectedContractId] = useState<string | null>(null);

  const [contractSearch, setContractSearch] = useState('');
  const [contractStateFilter, setContractStateFilter] = useState('');
  const filteredContracts = contracts.filter(c => {
    const q = contractSearch.toLowerCase();
    const matchesText = !q || c.title.toLowerCase().includes(q) || c.reference_number.toLowerCase().includes(q) || (c.counterparty || '').toLowerCase().includes(q) || c.state.toLowerCase().includes(q);
    const matchesState = !contractStateFilter || c.state === contractStateFilter;
    return matchesText && matchesState;
  });

  // Notifications / webhooks form
  const [whUrl, setWhUrl] = useState('');
  const [whEvent, setWhEvent] = useState('*');
  const [whSecret, setWhSecret] = useState('');

  const headers: Record<string, string> = token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };

  // The fetch helpers are component-local and recreated on render. Re-running
  // this bootstrap effect for each helper identity would create request loops;
  // token is the intentional lifecycle boundary for the authenticated shell.
  useEffect(() => {
    if (token) {
      fetchMe();
      fetchContracts();
      fetchTemplates();
      fetchUsers();
      fetchNotifications();
      fetchWebhooks();
      fetchEmailDeliveries();
      fetchSmsDeliveries();
      fetchAudit();
      fetchReporting();
      fetchIntelligence();
    }
  // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await fetch('/api/v1/identity/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.success) {
        const t = data.data.access_token;
        localStorage.setItem('eclms_token', t);
        setToken(t);
      } else {
        setLoginError(data.error?.message || 'Login failed');
      }
    } catch (err: any) {
      setLoginError(err.message || 'Network error');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('eclms_token');
    setToken(null);
    setUser(null);
  };

  const fetchMe = async () => {
    try {
      const res = await fetch('/api/v1/identity/auth/me', { headers });
      const data = await res.json();
      if (data.success) setUser(data.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchContracts = async () => {
    try {
      const res = await fetch('/api/v1/contracts?limit=200', { headers });
      const data = await res.json();
      if (data.success) setContracts(data.data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchTemplates = async () => {
    try { const res = await fetch('/api/v1/contracts/templates', { headers }); const data = await res.json(); if (data.success) setTemplates(data.data.items || []); } catch (e) { console.error(e); }
  };

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/v1/identity/users', { headers });
      const data = await res.json();
      if (data.success) setUsers(data.data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchNotifications = async () => {
    try {
      const [res, warningRes] = await Promise.all([
        fetch('/api/v1/notifications', { headers }),
        fetch('/api/v1/contracts/guarantees/warnings?days=30', { headers }),
      ]);
      const data = await res.json();
      const warningData = await warningRes.json();
      const guaranteeNotifications = warningData.success ? (warningData.data.items || []).map((item: any) => ({
        id: `guarantee-${item.id}`,
        subject: item.warning === 'RELEASE_OVERDUE' ? 'Guarantee release overdue' : 'Guarantee expiry warning',
        body: `${item.guarantee_type} guarantee ${item.serial_number} requires attention before ${item.expires_on}.`,
        channel: 'in_app', is_read: false, created_at: item.created_at,
      })) : [];
      if (data.success) setNotifications([...guaranteeNotifications, ...(data.data.items || [])]);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchWebhooks = async () => {
    try {
      const res = await fetch('/api/v1/notifications/webhooks', { headers });
      const data = await res.json();
      if (data.success) {
        setWebhooks(data.data.items || []);
        data.data.items?.forEach((w: any) => fetchWebhookDeliveries(w.id));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchWebhookDeliveries = async (webhookId: string) => {
    try {
      const res = await fetch(`/api/v1/notifications/webhooks/${webhookId}/deliveries?limit=25`, { headers });
      const data = await res.json();
      if (data.success) setWebhookDeliveries(prev => ({ ...prev, [webhookId]: data.data }));
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEmailDeliveries = async () => {
    try {
      const res = await fetch('/api/v1/notifications/email/deliveries?limit=25', { headers });
      const data = await res.json();
      if (data.success) setEmailDeliveries(data.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSmsDeliveries = async () => {
    try {
      const res = await fetch('/api/v1/notifications/sms/deliveries?limit=25', { headers });
      const data = await res.json();
      if (data.success) setSmsDeliveries(data.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAudit = async () => {
    try {
      const res = await fetch('/api/v1/audit', { headers });
      const data = await res.json();
      if (data.success) setAuditLogs(data.data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchReporting = async () => {
    try {
      const [res, trendRes] = await Promise.all([
        fetch('/api/v1/reporting/overview', { headers }),
        fetch('/api/v1/reporting/trends?months=6', { headers }),
      ]);
      const data = await res.json();
      const trendData = await trendRes.json();
      if (data.success) setReporting({ ...data.data, trends: trendData.success ? trendData.data.months : [] });
    } catch (e) {
      console.error(e);
    }
  };

  const fetchIntelligence = async () => {
    setRiskLoading(true);
    try {
      const [riskRes, alertsRes] = await Promise.all([
        fetch('/api/v1/intelligence/risk/overview', { headers }),
        fetch('/api/v1/intelligence/alerts', { headers })
      ]);
      const riskData = await riskRes.json();
      const alertsData = await alertsRes.json();
      if (riskData.success) setRiskOverview(riskData.data);
      if (alertsData.success) setAlerts(alertsData.data.alerts || []);
    } catch (e) {
      console.error(e);
    } finally {
      setRiskLoading(false);
    }
  };

  const handleAssessContractRisk = async (contractId: string) => {
    try {
      const res = await fetch(`/api/v1/intelligence/risk/contracts/${contractId}`, { headers });
      const data = await res.json();
      if (data.success) setContractRisk(data.data);
      else alert(data.error?.message || 'Risk assessment failed');
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAnalyzeClauses = async (contractId: string) => {
    try {
      const res = await fetch(`/api/v1/intelligence/clauses/${contractId}`, { headers });
      const data = await res.json();
      if (data.success) setClauseAnalysis(data.data);
      else alert(data.error?.message || 'Clause analysis failed');
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch(`/api/v1/intelligence/search?q=${encodeURIComponent(searchQuery)}&limit=10`, { headers });
      const data = await res.json();
      if (data.success) setSearchResults(data.data.results || []);
      else alert(data.error?.message || 'Search failed');
    } catch (err: any) {
      alert(err.message);
    }
  };

  const riskColor = (level: string) => {
    switch (level) {
      case 'CRITICAL': return { bg: '#fee2e2', color: '#991b1b' };
      case 'HIGH': return { bg: '#ffedd5', color: '#9a3412' };
      case 'MEDIUM': return { bg: '#fef3c7', color: '#92400e' };
      default: return { bg: '#dcfce7', color: '#166534' };
    }
  };

  const markNotificationRead = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/notifications/${id}/read`, { method: 'POST', headers });
      const data = await res.json();
      if (data.success) {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const res = await fetch('/api/v1/notifications/read-all', { method: 'POST', headers });
      const data = await res.json();
      if (data.success) {
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubscribeWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/notifications/webhooks', {
        method: 'POST',
        headers,
        body: JSON.stringify({ url: whUrl, event_type: whEvent, secret: whSecret })
      });
      const data = await res.json();
      if (data.success) {
        setWhUrl('');
        setWhSecret('');
        fetchWebhooks();
        alert('Webhook subscribed');
      } else {
        alert(data.error?.message || 'Failed to subscribe webhook');
      }
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCreateContract = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/contracts', {
        method: 'POST',
        headers,
        body: JSON.stringify({ title: newTitle, reference_number: newRef, counterparty: newCounterparty })
      });
      const data = await res.json();
      if (data.success) {
        setNewTitle('');
        setNewRef('');
        setNewCounterparty('');
        fetchContracts();
      } else {
        alert(data.error?.message || 'Failed to create contract');
      }
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/identity/users', {
        method: 'POST',
        headers,
        body: JSON.stringify({ username: newUsername, email: newEmail, full_name: newFullName, password: newPassword, role: newRole })
      });
      const data = await res.json();
      if (data.success) {
        setNewUsername('');
        setNewEmail('');
        setNewFullName('');
        fetchUsers();
        alert('User created successfully');
      } else {
        alert(data.error?.message || 'Failed to create user');
      }
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleStartWorkflow = async (contractId: string, defId: string = 'contract-approval') => {
    try {
      const res = await fetch('/api/v1/workflows/start', {
        method: 'POST',
        headers,
        body: JSON.stringify({ contract_id: contractId, definition_id: defId })
      });
      const data = await res.json();
      if (data.success) {
        setSelectedWorkflowId(data.data.id);
        setWorkflows(prev => ({ ...prev, [data.data.id]: data.data }));
        fetchContracts();
        setActiveTab('workflows');
      } else {
        alert(data.error?.message || 'Failed to start workflow');
      }
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleWorkflowTransition = async (workflowId: string, decision: 'APPROVE' | 'REJECT') => {
    try {
      const payload: any = { decision, comment: transitionComment };
      if (transitionStepName) payload.step_name = transitionStepName;

      const res = await fetch(`/api/v1/workflows/${workflowId}/transition`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        setWorkflows(prev => ({ ...prev, [workflowId]: data.data }));
        setTransitionComment('');
        setTransitionStepName('');
        fetchContracts();
        fetchWorkflowHistory(workflowId);
      } else {
        alert(data.error?.message || 'Transition failed');
      }
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleWorkflowPause = async (workflowId: string) => {
    if (!pauseReason) return alert('Enter reason');
    try {
      const res = await fetch(`/api/v1/workflows/${workflowId}/pause`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ reason: pauseReason })
      });
      const data = await res.json();
      if (data.success) {
        setWorkflows(prev => ({ ...prev, [workflowId]: data.data }));
        setPauseReason('');
        fetchWorkflowHistory(workflowId);
      } else {
        alert(data.error?.message);
      }
    } catch (e: any) { alert(e.message); }
  };

  const handleWorkflowResume = async (workflowId: string) => {
    try {
      const res = await fetch(`/api/v1/workflows/${workflowId}/resume`, {
        method: 'POST',
        headers
      });
      const data = await res.json();
      if (data.success) {
        setWorkflows(prev => ({ ...prev, [workflowId]: data.data }));
        fetchWorkflowHistory(workflowId);
      } else { alert(data.error?.message); }
    } catch (e: any) { alert(e.message); }
  };

  const handleWorkflowDelegate = async (workflowId: string) => {
    if (!delegateToUser) return alert('Select delegate user ID');
    try {
      const payload: any = { delegated_to: delegateToUser, comment: transitionComment };
      if (transitionStepName) payload.step_name = transitionStepName;
      const res = await fetch(`/api/v1/workflows/${workflowId}/delegate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        setWorkflows(prev => ({ ...prev, [workflowId]: data.data }));
        setDelegateToUser('');
        fetchWorkflowHistory(workflowId);
      } else { alert(data.error?.message); }
    } catch (e: any) { alert(e.message); }
  };

  const handleWorkflowEscalate = async (workflowId: string) => {
    try {
      const payload: any = { role: escalateRole, comment: transitionComment };
      if (transitionStepName) payload.step_name = transitionStepName;
      const res = await fetch(`/api/v1/workflows/${workflowId}/escalate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        setWorkflows(prev => ({ ...prev, [workflowId]: data.data }));
        fetchWorkflowHistory(workflowId);
      } else { alert(data.error?.message); }
    } catch (e: any) { alert(e.message); }
  };

  const fetchWorkflowHistory = async (workflowId: string) => {
    try {
      const res = await fetch(`/api/v1/workflows/${workflowId}/history`, { headers });
      const data = await res.json();
      if (data.success) setWorkflowHistory(data.data.items || []);
    } catch (e) { console.error(e); }
  };

  if (!token) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f8fafc', width: '100%' }}>
        <div style={{ background: '#fff', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)', width: '400px', textAlign: 'left' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <Shield size={36} color="#7c3aed" />
            <div>
              <h2 style={{ margin: 0, fontSize: '24px', color: '#1e293b' }}>ECLMS Portal</h2>
              <p style={{ fontSize: '14px', color: '#64748b' }}>Enterprise Contract Lifecycle Management</p>
            </div>
          </div>
          {loginError && (
            <div style={{ background: '#fee2e2', color: '#991b1b', padding: '10px', borderRadius: '6px', marginBottom: '16px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={16} /> {loginError}
            </div>
          )}
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>Username</label>
              <input 
                type="text" 
                value={username} 
                onChange={e => setUsername(e.target.value)} 
                style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }} 
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>Password</label>
              <input 
                type="password" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px', boxSizing: 'border-box' }} 
              />
            </div>
            <button type="submit" style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '12px', borderRadius: '6px', fontWeight: 600, fontSize: '15px', cursor: 'pointer', marginTop: '8px' }}>
              Sign In
            </button>
          </form>
          <div style={{ marginTop: '20px', fontSize: '12px', color: '#94a3b8', textAlign: 'center' }}>
            Default Admin: <code>admin</code> / <code>admin</code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', width: '100%', background: '#f8fafc', color: '#1e293b', textAlign: 'left' }}>
      {/* Top Navbar */}
      <header style={{ background: '#fff', borderBottom: '1px solid #e2e8f0', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Shield size={28} color="#7c3aed" />
          <h1 style={{ fontSize: '20px', margin: 0, fontWeight: 700, color: '#0f172a' }}>ECLMS Enterprise</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#f1f5f9', padding: '6px 12px', borderRadius: '20px', fontSize: '13px' }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>{user.full_name}</span>
              <span style={{ background: '#7c3aed', color: '#fff', padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 600 }}>{user.organization_id}</span>
            </div>
          )}
          <button 
            onClick={() => setActiveTab('notifications')}
            style={{ position: 'relative', background: 'none', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#475569' }}
          >
            <Bell size={14} /> Notifications
            {notifications.filter(n => !n.is_read).length > 0 && (
              <span style={{ position: 'absolute', top: '-8px', right: '-8px', background: '#dc2626', color: '#fff', borderRadius: '50%', width: '18px', height: '18px', fontSize: '11px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {notifications.filter(n => !n.is_read).length}
              </span>
            )}
          </button>
          <button onClick={() => setIsSettingsOpen(true)} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#475569' }}>
            <Settings size={14} /> LLM Settings
          </button>
          <button onClick={handleLogout} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#475569' }}>
            <LogOut size={14} /> Logout
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div style={{ background: '#fff', borderBottom: '1px solid #e2e8f0', padding: '0 32px', display: 'flex', gap: '28px', overflowX: 'auto', whiteSpace: 'nowrap' }}>
        {[ 
          { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard },
          { id: 'contracts', label: 'Contracts', icon: FileText },
          { id: 'approvals', label: 'Approval Inbox', icon: CheckCircle2 },
          { id: 'workflows', label: 'Workflows & Approvals', icon: GitBranch },
          { id: 'obligations', label: 'Obligations', icon: ClipboardCheck },
          { id: 'guarantees', label: 'Guarantees', icon: Shield },
          { id: 'finances', label: 'Finance', icon: Wallet },
          { id: 'users', label: 'Users & RBAC', icon: Users },
          { id: 'admin', label: 'Admin Center', icon: Settings },
          { id: 'notifications', label: 'Notifications & Webhooks', icon: Bell },
          { id: 'audit', label: 'Audit Trail', icon: Activity },
          { id: 'reporting', label: 'Analytics & Reporting', icon: BarChart3 },
          { id: 'intelligence', label: 'Intelligence', icon: Brain },
          { id: 'imports', label: 'Data Import', icon: Upload },
          { id: 'integrations', label: 'Integrations', icon: Plug },
          { id: 'system', label: 'System Health', icon: Activity },
        ].map(tab => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '14px 4px',
                background: 'none',
                border: 'none',
                borderBottom: active ? '2px solid #7c3aed' : '2px solid transparent',
                color: active ? '#7c3aed' : '#64748b',
                fontWeight: active ? 600 : 500,
                fontSize: '14px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                flexShrink: 0
              }}
            >
              <Icon size={16} /> {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Content */}
      <main style={{ padding: '32px', flex: 1, maxWidth: '1400px', width: '100%', boxSizing: 'border-box', margin: '0 auto' }}>

        {activeTab === 'dashboard' && (
          <DashboardTab
            reporting={reporting}
            riskOverview={riskOverview}
            alerts={alerts}
            notifications={notifications}
            contracts={contracts}
            onNavigate={tab => setActiveTab(tab as any)}
            onOpenContract={contractId => { setSelectedContractId(contractId); setActiveTab('contracts'); }}
          />
        )}

        {activeTab === 'approvals' && (
          <ApprovalInbox
            headers={headers}
            user={user}
            contracts={contracts}
            onOpenContract={contractId => { setSelectedContractId(contractId); setActiveTab('contracts'); }}
          />
        )}
        
        {/* CONTRACTS TAB */}
        {activeTab === 'contracts' && (
          <>
          <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '18px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><div><h2 style={{ margin: 0, fontSize: '18px' }}>Contract Template Library</h2><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '13px' }}>Reusable structures for fields, clauses, reviewers, SLAs, and required guarantees.</p></div><button onClick={fetchTemplates} style={{ background: '#fff', border: '1px solid #cbd5e1', padding: '7px 11px', borderRadius: '6px', cursor: 'pointer' }}>Refresh templates</button></div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px', marginTop: '14px' }}>{templates.map(template => <div key={template.key} style={{ border: '1px solid #ddd6fe', background: '#faf5ff', borderRadius: '8px', padding: '12px' }}><strong style={{ color: '#4c1d95' }}>{template.name}</strong><p style={{ fontSize: '12px', color: '#64748b', margin: '5px 0 9px' }}>{template.description}</p><div style={{ fontSize: '11px', color: '#475569' }}><strong>Fields:</strong> {(template.fields || []).map((f: any) => f.label).join(', ')}</div><div style={{ fontSize: '11px', color: '#475569', marginTop: '4px' }}><strong>Guarantees:</strong> {(template.required_guarantees || []).join(', ') || 'None'}</div></div>)}</div>
          </section>
          {selectedContractId && (
            <ContractPanel
              contractId={selectedContractId}
              headers={headers}
              onClose={() => setSelectedContractId(null)}
              onUpdated={fetchContracts}
            />
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '32px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '18px', margin: 0 }}>Active Contracts ({filteredContracts.length})</h2>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="text"
                    placeholder="Search title / ref / counterparty / state…"
                    value={contractSearch}
                    onChange={e => setContractSearch(e.target.value)}
                    style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', width: '260px' }}
                  />
                  <select value={contractStateFilter} onChange={e => setContractStateFilter(e.target.value)} style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', background: '#fff' }}>
                    <option value="">All states</option>
                    {Array.from(new Set(contracts.map(c => c.state))).map(s => <option key={s}>{s}</option>)}
                  </select>
                  <button onClick={fetchContracts} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                    <RefreshCw size={14} /> Refresh
                  </button>
                </div>
              </div>

              <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      <th style={{ padding: '12px 16px' }}>Title / Ref</th>
                      <th style={{ padding: '12px 16px' }}>Counterparty</th>
                      <th style={{ padding: '12px 16px' }}>State</th>
                      <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredContracts.length === 0 ? (
                      <tr><td colSpan={4} style={{ padding: '32px', textAlign: 'center', color: '#94a3b8' }}>No contracts found. Adjust the filters or create one using the form.</td></tr>
                    ) : filteredContracts.map(c => (
                      <tr key={c.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ fontWeight: 600, color: '#0f172a' }}>{c.title}</div>
                          <div style={{ fontSize: '12px', color: '#64748b' }}>{c.reference_number}</div>
                        </td>
                        <td style={{ padding: '14px 16px', color: '#334155' }}>{c.counterparty}</td>
                        <td style={{ padding: '14px 16px' }}>
                          <span style={{ 
                            padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600,
                            background: c.state === 'APPROVED' ? '#dcfce7' : c.state === 'REJECTED' ? '#fee2e2' : c.state === 'UNDER_REVIEW' ? '#fef3c7' : '#f1f5f9',
                            color: c.state === 'APPROVED' ? '#166534' : c.state === 'REJECTED' ? '#991b1b' : c.state === 'UNDER_REVIEW' ? '#92400e' : '#475569'
                          }}>
                            {c.state}
                          </span>
                        </td>
                        <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                          <button 
                            onClick={() => setSelectedContractId(c.id)}
                            style={{ background: '#f1f5f9', color: '#7c3aed', border: '1px solid #e9d5ff', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', marginRight: '6px' }}
                          >
                            Manage
                          </button>
                          {c.state === 'DRAFT' && (
                            <button 
                              onClick={() => handleStartWorkflow(c.id, newDefId)}
                              style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                            >
                              Start Workflow
                            </button>
                          )}
                          {c.state !== 'DRAFT' && (
                            <button 
                              onClick={() => setActiveTab('workflows')}
                              style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                            >
                              View Workflow
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Create Contract Form */}
            <div>
              <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <h3 style={{ fontSize: '16px', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Plus size={18} color="#7c3aed" /> New Contract
                </h3>
                <form onSubmit={handleCreateContract} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Title</label>
                    <input type="text" value={newTitle} onChange={e => setNewTitle(e.target.value)} required placeholder="e.g. Master Services Agreement" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Reference Number</label>
                    <input type="text" value={newRef} onChange={e => setNewRef(e.target.value)} required placeholder="e.g. MSA-2026-001" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Counterparty</label>
                    <input type="text" value={newCounterparty} onChange={e => setNewCounterparty(e.target.value)} required placeholder="e.g. Acme Corp" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Initial Workflow Blueprint</label>
                    <select value={newDefId} onChange={e => setNewDefId(e.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box', background: '#fff' }}>
                      <option value="contract-approval">Standard Approval (Sequential)</option>
                      <option value="contract-approval-parallel">Parallel Review (Legal + Compliance)</option>
                      <option value="contract-approval-conditional">Conditional (CFO if Acme)</option>
                    </select>
                  </div>
                  <button type="submit" style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', fontWeight: 600, fontSize: '14px', cursor: 'pointer', marginTop: '6px' }}>
                    Create Contract
                  </button>
                </form>
              </div>
            </div>
          </div>
          </>
        )}

        {/* WORKFLOWS TAB */}
        {activeTab === 'workflows' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '18px', margin: 0 }}>Workflow & Approval Engine</h2>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input 
                  type="text" 
                  placeholder="Enter Workflow ID" 
                  value={selectedWorkflowId || ''} 
                  onChange={e => setSelectedWorkflowId(e.target.value)} 
                  style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', width: '280px' }} 
                />
                <button 
                  onClick={() => { if (selectedWorkflowId) { fetchWorkflowHistory(selectedWorkflowId); fetch(`/api/v1/workflows/${selectedWorkflowId}`, { headers }).then(r=>r.json()).then(d => { if(d.success) setWorkflows(prev=>({...prev, [selectedWorkflowId]: d.data})) }); } }}
                  style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '6px', fontWeight: 600, fontSize: '13px', cursor: 'pointer' }}
                >
                  Load Workflow
                </button>
              </div>
            </div>

            {selectedWorkflowId && workflows[selectedWorkflowId] ? (() => {
              const wf = workflows[selectedWorkflowId];
              return (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '32px' }}>
                  <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #f1f5f9', paddingBottom: '16px' }}>
                      <div>
                        <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>WORKFLOW INSTANCE</div>
                        <div style={{ fontFamily: 'monospace', fontSize: '15px', fontWeight: 600, color: '#0f172a' }}>{wf.id}</div>
                      </div>
                      <span style={{ 
                        padding: '6px 14px', borderRadius: '20px', fontSize: '13px', fontWeight: 600,
                        background: wf.status === 'APPROVED' ? '#dcfce7' : wf.status === 'REJECTED' ? '#fee2e2' : wf.status === 'PAUSED' ? '#fef3c7' : '#e0e7ff',
                        color: wf.status === 'APPROVED' ? '#166534' : wf.status === 'REJECTED' ? '#991b1b' : wf.status === 'PAUSED' ? '#92400e' : '#3730a3'
                      }}>
                        {wf.status}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '15px', marginBottom: '16px' }}>Approval Steps & Status</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                      {wf.steps.map((s, idx) => (
                        <div key={idx} style={{ padding: '14px 16px', borderRadius: '8px', border: '1px solid #e2e8f0', background: s.name === wf.current_step ? '#faf5ff' : '#f8fafc', borderColor: s.name === wf.current_step ? '#d8b4fe' : '#e2e8f0' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>{idx + 1}. {s.name}</span>
                              {s.parallel_group_id && <span style={{ background: '#e0e7ff', color: '#3730a3', fontSize: '11px', padding: '2px 6px', borderRadius: '4px' }}>Parallel: {s.parallel_group_id}</span>}
                            </div>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: s.status === 'APPROVED' ? '#166534' : s.status === 'REJECTED' ? '#991b1b' : s.status === 'SKIPPED' ? '#64748b' : '#7c3aed' }}>
                              {s.status}
                            </span>
                          </div>
                          <div style={{ fontSize: '13px', color: '#64748b', display: 'flex', gap: '16px' }}>
                            <span>Role: <strong>{s.assigned_role}</strong></span>
                            {s.delegated_to && <span>Delegated To: <code>{s.delegated_to}</code></span>}
                            {s.decided_by && <span>Decided By: <code>{s.decided_by}</code></span>}
                          </div>
                          {s.comment && <div style={{ marginTop: '8px', fontSize: '13px', background: '#fff', padding: '6px 10px', borderRadius: '4px', border: '1px solid #cbd5e1', color: '#334155' }}>"{s.comment}"</div>}
                        </div>
                      ))}
                    </div>

                    <h3 style={{ fontSize: '15px', marginBottom: '12px' }}>Execution History Log</h3>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', maxHeight: '200px', overflowY: 'auto', fontSize: '13px' }}>
                      {workflowHistory.length === 0 ? (
                        <div style={{ color: '#94a3b8', textAlign: 'center', padding: '10px' }}>Click "Load Workflow History" below to view audit trail.</div>
                      ) : workflowHistory.map((h, i) => (
                        <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between' }}>
                          <span><strong>{h.from_state}</strong> → <strong>{h.to_state}</strong> ({h.reason || 'no comment'})</span>
                          <span style={{ color: '#64748b', fontSize: '11px' }}>{h.actor_id}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Workflow Control Actions */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {wf.status === 'RUNNING' && (
                      <div style={{ background: '#fff', padding: '20px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                        <h3 style={{ fontSize: '15px', margin: '0 0 14px' }}>Step Decision</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Target Step Name (Optional for Parallel)</label>
                            <input type="text" placeholder="e.g. Legal Review" value={transitionStepName} onChange={e => setTransitionStepName(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                          </div>
                          <div>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Comment / Reason</label>
                            <input type="text" placeholder="e.g. Approved per terms" value={transitionComment} onChange={e => setTransitionComment(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                          </div>
                          <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                            <button onClick={() => handleWorkflowTransition(wf.id, 'APPROVE')} style={{ flex: 1, background: '#16a34a', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px' }}>
                              <CheckCircle2 size={16} /> Approve
                            </button>
                            <button onClick={() => handleWorkflowTransition(wf.id, 'REJECT')} style={{ flex: 1, background: '#dc2626', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px' }}>
                              <XCircle size={16} /> Reject
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Phase 2 Advanced Controls */}
                    <div style={{ background: '#fff', padding: '20px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                      <h3 style={{ fontSize: '15px', margin: '0 0 14px' }}>Phase 2 Advanced Controls</h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        {wf.status === 'RUNNING' && (
                          <div>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Pause Reason</label>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <input type="text" placeholder="Reason..." value={pauseReason} onChange={e => setPauseReason(e.target.value)} style={{ flex: 1, padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px' }} />
                              <button onClick={() => handleWorkflowPause(wf.id)} style={{ background: '#d97706', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', fontWeight: 600, fontSize: '12px', cursor: 'pointer' }}>Pause</button>
                            </div>
                          </div>
                        )}
                        {wf.status === 'PAUSED' && (
                          <button onClick={() => handleWorkflowResume(wf.id)} style={{ background: '#2563eb', color: '#fff', border: 'none', padding: '8px', borderRadius: '6px', fontWeight: 600, fontSize: '13px', cursor: 'pointer', width: '100%' }}>
                            Resume Workflow
                          </button>
                        )}
                        <div>
                          <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Delegate Step to User ID</label>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <input type="text" placeholder="User UUID..." value={delegateToUser} onChange={e => setDelegateToUser(e.target.value)} style={{ flex: 1, padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px' }} />
                            <button onClick={() => handleWorkflowDelegate(wf.id)} style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', fontWeight: 600, fontSize: '12px', cursor: 'pointer' }}>Delegate</button>
                          </div>
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Escalate Step to Role</label>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <select value={escalateRole} onChange={e => setEscalateRole(e.target.value)} style={{ flex: 1, padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px', background: '#fff' }}>
                              <option value="ADMIN">ADMIN</option>
                              <option value="CONTRACT_MANAGER">CONTRACT_MANAGER</option>
                            </select>
                            <button onClick={() => handleWorkflowEscalate(wf.id)} style={{ background: '#475569', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', fontWeight: 600, fontSize: '12px', cursor: 'pointer' }}>Escalate</button>
                          </div>
                        </div>
                        <button onClick={() => fetchWorkflowHistory(wf.id)} style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', padding: '8px', borderRadius: '6px', fontWeight: 600, fontSize: '13px', cursor: 'pointer', width: '100%', marginTop: '4px' }}>
                          Load Workflow History
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })() : (
              <div style={{ background: '#fff', padding: '48px', textAlign: 'center', borderRadius: '10px', border: '1px solid #e2e8f0', color: '#64748b' }}>
                Select a workflow from the Contracts tab or enter a Workflow ID above.
              </div>
            )}
          </div>
        )}

        {/* OBLIGATIONS TAB */}
        {activeTab === 'obligations' && (
          <ObligationsTab headers={headers} contracts={contracts} />
        )}

        {activeTab === 'guarantees' && <GuaranteesTab headers={headers} contracts={contracts} />}

        {/* FINANCE TAB */}
        {activeTab === 'finances' && (
          <FinancesTab headers={headers} contracts={contracts} />
        )}

        {activeTab === 'imports' && (
          <DataImportTab headers={headers} contracts={contracts} />
        )}

        {activeTab === 'integrations' && (
          <IntegrationsTab headers={headers} />
        )}

        {activeTab === 'admin' && (
          <AdminCenterTab user={user} users={users} headers={headers} onNavigate={tab => setActiveTab(tab as any)} onOpenSettings={() => setIsSettingsOpen(true)} />
        )}

        {/* USERS TAB */}
        {activeTab === 'users' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '32px' }}>
            <div>
              <h2 style={{ fontSize: '18px', marginBottom: '20px' }}>Organization Users & Roles</h2>
              <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', fontSize: '12px', textTransform: 'uppercase' }}>
                      <th style={{ padding: '12px 16px' }}>Full Name / Username</th>
                      <th style={{ padding: '12px 16px' }}>Email</th>
                      <th style={{ padding: '12px 16px' }}>Assigned Roles</th>
                      <th style={{ padding: '12px 16px' }}>User ID</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ fontWeight: 600, color: '#0f172a' }}>{u.full_name}</div>
                          <div style={{ fontSize: '12px', color: '#64748b' }}>{u.username}</div>
                        </td>
                        <td style={{ padding: '14px 16px', color: '#334155' }}>{u.email}</td>
                        <td style={{ padding: '14px 16px' }}>
                          {u.roles?.map(r => (
                            <span key={r} style={{ background: '#e0e7ff', color: '#3730a3', fontSize: '11px', padding: '2px 8px', borderRadius: '10px', fontWeight: 600, marginRight: '4px' }}>
                              {r}
                            </span>
                          ))}
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <code style={{ fontSize: '11px', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>{u.id}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Create User Form */}
            <div>
              <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <h3 style={{ fontSize: '16px', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <UserPlus size={18} color="#7c3aed" /> Provision User
                </h3>
                <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Username</label>
                    <input type="text" value={newUsername} onChange={e => setNewUsername(e.target.value)} required placeholder="e.g. jmanager" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Email</label>
                    <input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} required placeholder="user@eclms.local" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Full Name</label>
                    <input type="text" value={newFullName} onChange={e => setNewFullName(e.target.value)} required placeholder="Jane Manager" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Password</label>
                    <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Role</label>
                    <select value={newRole} onChange={e => setNewRole(e.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box', background: '#fff' }}>
                      <option value="CONTRACT_MANAGER">CONTRACT_MANAGER</option>
                      <option value="ADMIN">ADMIN</option>
                      <option value="VIEWER">VIEWER</option>
                    </select>
                  </div>
                  <button type="submit" style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', fontWeight: 600, fontSize: '14px', cursor: 'pointer', marginTop: '6px' }}>
                    Create User
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

      {/* NOTIFICATIONS & WEBHOOKS TAB */}
        {activeTab === 'notifications' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '18px', margin: 0 }}>Notifications & Webhooks</h2>
              <button onClick={() => { fetchNotifications(); fetchWebhooks(); fetchEmailDeliveries(); fetchSmsDeliveries(); }} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <RefreshCw size={14} /> Refresh
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '32px' }}>
              {/* In-app notifications */}
              <div>
                <h3 style={{ fontSize: '15px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Bell size={16} color="#7c3aed" /> In-App Notifications
                  {notifications.filter(n => !n.is_read).length > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      style={{ marginLeft: 'auto', background: '#7c3aed', color: '#fff', border: 'none', padding: '4px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}
                    >
                      Mark All Read
                    </button>
                  )}
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {notifications.length === 0 ? (
                    <div style={{ background: '#fff', padding: '32px', textAlign: 'center', borderRadius: '10px', border: '1px solid #e2e8f0', color: '#94a3b8' }}>
                      No notifications yet. Workflow and contract events will appear here.
                    </div>
                  ) : notifications.map(n => (
                    <div key={n.id} onClick={() => markNotificationRead(n.id)} style={{
                      background: '#fff', padding: '14px 16px', borderRadius: '10px', border: '1px solid #e2e8f0',
                      cursor: 'pointer', opacity: n.is_read ? 0.6 : 1, borderLeft: n.is_read ? '4px solid #e2e8f0' : '4px solid #7c3aed'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>{n.subject}</span>
                        <span style={{ fontSize: '11px', color: '#64748b', background: '#f1f5f9', padding: '2px 8px', borderRadius: '10px' }}>{n.channel}</span>
                      </div>
                      <div style={{ fontSize: '13px', color: '#475569' }}>{n.body}</div>
                      {!n.is_read && <div style={{ marginTop: '6px', fontSize: '11px', color: '#7c3aed', fontWeight: 600 }}>Click to mark as read</div>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Webhook subscriptions */}
              <div>
                <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', marginBottom: '20px' }}>
                  <h3 style={{ fontSize: '16px', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Webhook size={18} color="#7c3aed" /> Subscribe Webhook
                  </h3>
                  <form onSubmit={handleSubscribeWebhook} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Endpoint URL</label>
                      <input type="text" value={whUrl} onChange={e => setWhUrl(e.target.value)} required placeholder="https://your-system.com/hook" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Event Type</label>
                      <select value={whEvent} onChange={e => setWhEvent(e.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box', background: '#fff' }}>
                        <option value="*">All events (*)</option>
                        <option value="contract.created">contract.created</option>
                        <option value="contract.state_changed">contract.state_changed</option>
                        <option value="workflow.started">workflow.started</option>
                        <option value="workflow.step_decided">workflow.step_decided</option>
                        <option value="workflow.paused">workflow.paused</option>
                        <option value="document.uploaded">document.uploaded</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Signing Secret</label>
                      <input type="password" value={whSecret} onChange={e => setWhSecret(e.target.value)} required placeholder="min 6 characters" style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' }} />
                    </div>
                    <button type="submit" style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', fontWeight: 600, fontSize: '14px', cursor: 'pointer' }}>
                      Subscribe
                    </button>
                  </form>
                </div>

                <div style={{ background: '#fff', padding: '20px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                  <h3 style={{ fontSize: '15px', margin: '0 0 12px' }}>Active Webhooks</h3>
                  {webhooks.length === 0 ? (
                    <div style={{ fontSize: '13px', color: '#94a3b8', textAlign: 'center', padding: '12px' }}>No webhook subscriptions.</div>
                  ) : webhooks.map(w => {
                    const dlv = webhookDeliveries[w.id];
                    return (
                    <div key={w.id} style={{ padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '8px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>{w.event_type}</code>
                        <span style={{ color: w.is_active === false ? '#94a3b8' : '#16a34a', fontWeight: 600 }}>{w.is_active === false ? 'inactive' : 'active'}</span>
                      </div>
                      <div style={{ color: '#475569', marginTop: '4px', wordBreak: 'break-all' }}>{w.url}</div>
                      {dlv && (
                        <div style={{ marginTop: '8px', display: 'flex', gap: '12px', fontSize: '12px' }}>
                          <span style={{ color: '#64748b' }}>Deliveries: <strong>{dlv.total || 0}</strong></span>
                          <span style={{ color: (dlv.failed || 0) > 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                            Failed: {dlv.failed || 0}
                          </span>
                          <button
                            onClick={() => fetchWebhookDeliveries(w.id)}
                            style={{ marginLeft: 'auto', background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                          >
                            Refresh
                          </button>
                        </div>
                      )}
                    </div>
                    );
                  })}
                </div>

                <div style={{ background: '#fff', padding: '20px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                  <h3 style={{ fontSize: '15px', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Mail size={16} color="#7c3aed" /> Email Deliveries
                  </h3>
                  {!emailDeliveries ? (
                    <div style={{ fontSize: '13px', color: '#94a3b8', textAlign: 'center', padding: '12px' }}>No email deliveries recorded.</div>
                  ) : (
                    <>
                      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', fontSize: '13px' }}>
                        <span style={{ color: '#64748b' }}>Total: <strong>{emailDeliveries.total || 0}</strong></span>
                        <span style={{ color: (emailDeliveries.failed || 0) > 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                          Failed: {emailDeliveries.failed || 0}
                        </span>
                        <span style={{ color: '#16a34a' }}>Sent: {emailDeliveries.sent || 0}</span>
                        <button
                          onClick={fetchEmailDeliveries}
                          style={{ marginLeft: 'auto', background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                        >
                          Refresh
                        </button>
                      </div>
                      {emailDeliveries.items?.length === 0 ? (
                        <div style={{ fontSize: '12px', color: '#94a3b8', textAlign: 'center', padding: '8px' }}>No deliveries yet.</div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '260px', overflowY: 'auto' }}>
                          {emailDeliveries.items?.map((d: any) => (
                            <div key={d.id} style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontWeight: 600, color: '#0f172a' }}>{d.subject}</span>
                                <span style={{ color: d.status === 'sent' ? '#16a34a' : '#dc2626', fontWeight: 600 }}>{d.status}</span>
                              </div>
                              <div style={{ color: '#475569', marginTop: '2px' }}>{d.recipient_email}</div>
                              <div style={{ color: '#94a3b8', marginTop: '2px' }}>{d.event_type}{d.error ? ` · ${d.error}` : ''}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>

                <div style={{ background: '#fff', padding: '20px', borderRadius: '10px', border: '1px solid #e2e8f0', marginTop: '20px' }}>
                  <h3 style={{ fontSize: '15px', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <MessageSquare size={16} color="#7c3aed" /> SMS Deliveries
                  </h3>
                  {!smsDeliveries ? (
                    <div style={{ fontSize: '13px', color: '#94a3b8', textAlign: 'center', padding: '12px' }}>No SMS deliveries recorded.</div>
                  ) : (
                    <>
                      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', fontSize: '13px' }}>
                        <span style={{ color: '#64748b' }}>Total: <strong>{smsDeliveries.total || 0}</strong></span>
                        <span style={{ color: (smsDeliveries.failed || 0) > 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                          Failed: {smsDeliveries.failed || 0}
                        </span>
                        <span style={{ color: '#16a34a' }}>Sent: {smsDeliveries.sent || 0}</span>
                        <button
                          onClick={fetchSmsDeliveries}
                          style={{ marginLeft: 'auto', background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                        >
                          Refresh
                        </button>
                      </div>
                      {smsDeliveries.items?.length === 0 ? (
                        <div style={{ fontSize: '12px', color: '#94a3b8', textAlign: 'center', padding: '8px' }}>No deliveries yet.</div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '260px', overflowY: 'auto' }}>
                          {smsDeliveries.items?.map((d: any) => (
                            <div key={d.id} style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontWeight: 600, color: '#0f172a' }}>{d.recipient_phone}</span>
                                <span style={{ color: d.status === 'sent' ? '#16a34a' : '#dc2626', fontWeight: 600 }}>{d.status}</span>
                              </div>
                              <div style={{ color: '#475569', marginTop: '2px' }}>{d.body}</div>
                              <div style={{ color: '#94a3b8', marginTop: '2px' }}>{d.event_type}{d.error ? ` · ${d.error}` : ''}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* AUDIT TRAIL TAB */}
        {activeTab === 'audit' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '18px', margin: 0 }}>Immutable Audit Trail (Article VIII)</h2>
                <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Append-only record of all system events and domain transitions.</p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={fetchAudit} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                  <RefreshCw size={14} /> Refresh
                </button>
                <button onClick={() => downloadAuthenticated('/api/v1/audit/export.csv?limit=500', { Authorization: `Bearer ${token}` }, `audit_export_${Date.now()}.csv`)} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                  <Download size={14} /> Export CSV
                </button>
              </div>
            </div>

            <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                    <th style={{ padding: '12px 16px' }}>Timestamp</th>
                    <th style={{ padding: '12px 16px' }}>Event Type</th>
                    <th style={{ padding: '12px 16px' }}>Module</th>
                    <th style={{ padding: '12px 16px' }}>Entity</th>
                    <th style={{ padding: '12px 16px' }}>Actor ID</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: '#94a3b8' }}>No audit records found.</td>
                    </tr>
                  ) : auditLogs.map(a => (
                    <tr key={a.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '12px 16px', color: '#64748b', whiteSpace: 'nowrap' }}>{new Date(a.created_at).toLocaleString()}</td>
                      <td style={{ padding: '12px 16px' }}><code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', color: '#7c3aed', fontWeight: 600 }}>{a.event_type}</code></td>
                      <td style={{ padding: '12px 16px', color: '#334155' }}>{a.source_module}</td>
                      <td style={{ padding: '12px 16px', color: '#475569' }}>{a.entity_type ? `${a.entity_type}: ${a.entity_id}` : '-'}</td>
                      <td style={{ padding: '12px 16px', color: '#64748b', fontFamily: 'monospace' }}>{a.actor_id || 'system'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ANALYTICS & REPORTING TAB */}
        {activeTab === 'reporting' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '18px', margin: 0 }}>Executive Intelligence & Analytics (RPT-022)</h2>
                <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Read-optimized overview of operational, workflow, obligation, and financial metrics.</p>
              </div>
              <button onClick={fetchReporting} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <RefreshCw size={14} /> Refresh Analytics
              </button>
              <button onClick={() => downloadAuthenticated('/api/v1/reporting/export.csv', headers, 'eclms-report.csv')} style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600 }}>
                Download CSV
              </button>
            </div>

            {!reporting ? (
              <div style={{ background: '#fff', padding: '48px', textAlign: 'center', borderRadius: '10px', border: '1px solid #e2e8f0', color: '#64748b' }}>
                Loading analytics report...
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
                {/* Contracts Card */}
                <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
                    <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                      <FileText size={18} color="#7c3aed" /> Contract Analytics
                    </h3>
                    <span style={{ fontSize: '20px', fontWeight: 700, color: '#7c3aed' }}>{reporting.contracts?.total_contracts || 0} Total</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Active Contracts</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: '#166534', marginTop: '4px' }}>{reporting.contracts?.active || 0}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Avg Lifecycle (Days)</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: '#3b82f6', marginTop: '4px' }}>{reporting.contracts?.avg_lifecycle_days ?? 'N/A'}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>Distribution by State:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(reporting.contracts?.by_state || {}).map(([state, count]) => (
                      <span key={state} style={{ background: '#f1f5f9', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', color: '#334155' }}>
                        <strong>{state}</strong>: {count as number}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Workflows Card */}
                <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
                    <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                      <GitBranch size={18} color="#7c3aed" /> Workflow Engine
                    </h3>
                    <span style={{ fontSize: '20px', fontWeight: 700, color: '#7c3aed' }}>{reporting.workflows?.total_workflows || 0} Total</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Avg Step Duration</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: '#3b82f6', marginTop: '4px' }}>{reporting.workflows?.avg_step_days ?? 0} days</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Approved Ratio</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: '#166534', marginTop: '4px' }}>
                        {reporting.workflows?.total_workflows ? Math.round(((reporting.workflows?.by_status?.APPROVED || 0) / reporting.workflows.total_workflows) * 100) : 0}%
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>Status Breakdown:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(reporting.workflows?.by_status || {}).map(([status, count]) => (
                      <span key={status} style={{ background: '#f1f5f9', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', color: '#334155' }}>
                        <strong>{status}</strong>: {count as number}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Obligations Card */}
                <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
                    <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                      <CheckCircle2 size={18} color="#7c3aed" /> Obligation Tracking
                    </h3>
                    <span style={{ fontSize: '20px', fontWeight: 700, color: '#7c3aed' }}>{reporting.obligations?.total_obligations || 0} Total</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Overdue Obligations</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: reporting.obligations?.overdue ? '#dc2626' : '#166534', marginTop: '4px' }}>
                        {reporting.obligations?.overdue || 0}
                      </div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>SLA Compliance Rate</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: '#3b82f6', marginTop: '4px' }}>
                        {reporting.obligations?.sla_compliance_rate !== null && reporting.obligations?.sla_compliance_rate !== undefined ? `${Math.round(reporting.obligations.sla_compliance_rate * 100)}%` : 'N/A'}
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>Obligation Statuses:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(reporting.obligations?.by_status || {}).map(([st, cnt]) => (
                      <span key={st} style={{ background: '#f1f5f9', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', color: '#334155' }}>
                        <strong>{st}</strong>: {cnt as number}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Finances Card */}
                <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
                    <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                      <Activity size={18} color="#7c3aed" /> Financial Exposure & Payments
                    </h3>
                    <span style={{ fontSize: '20px', fontWeight: 700, color: '#7c3aed' }}>${(reporting.finances?.total_value || 0).toLocaleString()} Value</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Total Paid</div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: '#166534', marginTop: '4px' }}>${(reporting.finances?.paid || 0).toLocaleString()}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Active Exposure</div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: '#d97706', marginTop: '4px' }}>${(reporting.finances?.active_exposure || 0).toLocaleString()}</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Completion Rate</div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: '#3b82f6', marginTop: '4px' }}>
                        {reporting.finances?.payment_completion_rate !== null && reporting.finances?.payment_completion_rate !== undefined ? `${Math.round(reporting.finances.payment_completion_rate * 100)}%` : '0%'}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#64748b', background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                    <span>Total Scheduled Installments: <strong>{reporting.finances?.total_payments || 0}</strong></span>
                    <span>Overdue Payments: <strong style={{ color: reporting.finances?.overdue_payments ? '#dc2626' : '#166534' }}>{reporting.finances?.overdue_payments || 0}</strong></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* INTELLIGENCE TAB */}
        {activeTab === 'intelligence' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h2 style={{ fontSize: '18px', margin: 0 }}>Intelligence & Optimization</h2>
                <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Risk detection, clause analysis, semantic search, and predictive alerts.</p>
              </div>
              <button onClick={fetchIntelligence} style={{ background: 'none', border: '1px solid #cbd5e1', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <RefreshCw size={14} /> Refresh Intelligence
              </button>
            </div>

            {/* Risk Overview */}
            <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', marginBottom: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
                <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                  <AlertTriangle size={18} color="#d97706" /> Portfolio Risk Overview
                </h3>
                <div style={{ display: 'flex', gap: '20px', fontSize: '14px' }}>
                  <span>Contracts Assessed: <strong>{riskOverview?.total_contracts_assessed ?? 0}</strong></span>
                  <span>High/Critical: <strong style={{ color: (riskOverview?.high_or_critical_risk_contracts || 0) > 0 ? '#dc2626' : '#166534' }}>{riskOverview?.high_or_critical_risk_contracts ?? 0}</strong></span>
                  <span>Avg Score: <strong style={{ color: '#3b82f6' }}>{riskOverview?.average_portfolio_risk_score ?? 0}</strong></span>
                </div>
              </div>

              {riskLoading ? (
                <div style={{ color: '#64748b', fontSize: '13px' }}>Assessing portfolio risk...</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', fontSize: '11px', textTransform: 'uppercase' }}>
                        <th style={{ padding: '10px 12px' }}>Contract</th>
                        <th style={{ padding: '10px 12px' }}>State</th>
                        <th style={{ padding: '10px 12px' }}>Score</th>
                        <th style={{ padding: '10px 12px' }}>Risk Level</th>
                        <th style={{ padding: '10px 12px' }}>Factors</th>
                        <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(riskOverview?.contracts || []).length === 0 ? (
                        <tr><td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>
                          No contracts to assess. Create contracts in the Contracts tab.
                        </td></tr>
                      ) : riskOverview.contracts.map((c: any) => (
                        <tr key={c.contract_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '12px', fontWeight: 600, color: '#0f172a' }}>{c.title}</td>
                          <td style={{ padding: '12px', color: '#334155' }}>{c.state}</td>
                          <td style={{ padding: '12px', fontWeight: 700, color: '#3b82f6' }}>{c.overall_score}</td>
                          <td style={{ padding: '12px' }}>
                            <span style={{ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, background: riskColor(c.risk_level).bg, color: riskColor(c.risk_level).color }}>
                              {c.risk_level}
                            </span>
                          </td>
                          <td style={{ padding: '12px', color: '#64748b' }}>{c.risk_factors_count}</td>
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            <button
                              onClick={() => handleAssessContractRisk(c.contract_id)}
                              style={{ background: '#f1f5f9', color: '#7c3aed', border: '1px solid #e9d5ff', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 600, cursor: 'pointer', marginRight: '6px' }}
                            >
                              Assess
                            </button>
                            <button
                              onClick={() => handleAnalyzeClauses(c.contract_id)}
                              style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 600, cursor: 'pointer' }}
                            >
                              Analyze Clauses
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Assessed Contract Detail */}
            {contractRisk && (
              <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', marginBottom: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '12px' }}>
                  <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                    <AlertTriangle size={18} color="#d97706" /> Risk Assessment — Contract {contractRisk.entity_id?.slice(0, 8)}
                    <span style={{ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, background: riskColor(contractRisk.risk_level).bg, color: riskColor(contractRisk.risk_level).color }}>
                      {contractRisk.risk_level} · {contractRisk.overall_score}/100
                    </span>
                  </h3>
                  <button onClick={() => setContractRisk(null)} style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>Dismiss</button>
                </div>
                {contractRisk.risk_factors?.length === 0 ? (
                  <div style={{ color: '#94a3b8', fontSize: '13px' }}>No material risk factors identified for this contract.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {contractRisk.risk_factors.map((f: any, i: number) => (
                      <div key={i} style={{ padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', borderLeft: '4px solid ' + riskColor(f.severity).color, background: '#f8fafc' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 700, fontSize: '12px', color: '#0f172a' }}>
                            <code style={{ background: '#f1f5f9', padding: '1px 6px', borderRadius: '4px', marginRight: '8px' }}>{f.category}</code>
                            {f.code}
                          </span>
                          <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 700, background: riskColor(f.severity).bg, color: riskColor(f.severity).color }}>
                            {f.severity} · +{f.score_impact}
                          </span>
                        </div>
                        <div style={{ fontSize: '13px', color: '#334155' }}>{f.message}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Clauses + Search side-by-side */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
              {/* Clause Analysis */}
              <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <h3 style={{ fontSize: '16px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                  <FileSearch size={18} color="#7c3aed" /> Clause Analysis
                </h3>
                {!clauseAnalysis ? (
                  <div style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', padding: '24px' }}>
                    Select "Analyze Clauses" on a contract above to parse its clauses.
                  </div>
                ) : (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#64748b', marginBottom: '12px', background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                      <span>Version {clauseAnalysis.version_number} — {clauseAnalysis.total_clauses} clauses</span>
                      <span>High Risk: <strong style={{ color: clauseAnalysis.high_risk_clauses_count ? '#dc2626' : '#166534' }}>{clauseAnalysis.high_risk_clauses_count}</strong></span>
                    </div>
                    {clauseAnalysis.note && <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '10px' }}>{clauseAnalysis.note}</div>}
                    {clauseAnalysis.missing_recommended_types?.length > 0 && (
                      <div style={{ marginBottom: '12px', fontSize: '12px' }}>
                        <span style={{ fontWeight: 600, color: '#92400e' }}>Missing recommended clauses:</span>{' '}
                        {clauseAnalysis.missing_recommended_types.map((m: string) => (
                          <span key={m} style={{ background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: '10px', fontWeight: 600, marginRight: '4px', fontSize: '11px' }}>{m}</span>
                        ))}
                      </div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '320px', overflowY: 'auto' }}>
                      {clauseAnalysis.clauses?.map((cl: any, i: number) => (
                        <div key={i} style={{ padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', background: '#f8fafc' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontWeight: 600, fontSize: '12px', color: '#0f172a' }}>{cl.title}</span>
                            <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 700, background: riskColor(cl.risk_level).bg, color: riskColor(cl.risk_level).color }}>
                              {cl.risk_level}
                            </span>
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b' }}>{cl.analysis_notes}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Predictive Alerts */}
              <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <h3 style={{ fontSize: '16px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                  <Bell size={18} color="#7c3aed" /> Predictive Alerts ({alerts.length})
                </h3>
                {alerts.length === 0 ? (
                  <div style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', padding: '24px' }}>
                    No predictive alerts. Expiring contracts, due obligations, and high-risk contracts appear here.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '360px', overflowY: 'auto' }}>
                    {alerts.map((a, i) => (
                      <div key={i} style={{ padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', borderLeft: '4px solid ' + (a.severity === 'CRITICAL' ? '#dc2626' : a.severity === 'HIGH' ? '#d97706' : a.severity === 'MEDIUM' ? '#d97706' : '#16a34a'), background: '#f8fafc' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: (a.severity === 'CRITICAL' ? '#dc2626' : a.severity === 'HIGH' ? '#d97706' : '#166534') }}>
                            {a.alert_type.replace('.', ' · ')}
                          </span>
                          <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 700, background: riskColor(a.severity).bg, color: riskColor(a.severity).color }}>{a.severity}</span>
                        </div>
                        <div style={{ fontSize: '13px', color: '#334155' }}>{a.message}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Semantic Search */}
            <div style={{ background: '#fff', padding: '24px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <h3 style={{ fontSize: '16px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px', color: '#0f172a' }}>
                <Search size={18} color="#7c3aed" /> Semantic Contract Search
              </h3>
              <form onSubmit={handleSemanticSearch} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="e.g. indemnification liability cap payment terms"
                  style={{ flex: 1, padding: '10px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }}
                />
                <button type="submit" style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: '6px', fontWeight: 600, cursor: 'pointer' }}>
                  Search
                </button>
              </form>
              {searchResults.length === 0 ? (
                <div style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', padding: '16px' }}>
                  Search results appear here. Contracts must have version text content to be indexable.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {searchResults.map((r, i) => (
                    <div key={i} style={{ padding: '12px 14px', borderRadius: '8px', border: '1px solid #e2e8f0', background: '#f8fafc' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontWeight: 600, fontSize: '14px', color: '#0f172a' }}>{r.title}</span>
                        <span style={{ background: '#e0e7ff', color: '#3730a3', fontSize: '11px', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>
                          {(r.similarity_score * 100).toFixed(1)}% match
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>{r.snippet}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'system' && (
          <SystemHealthTab headers={{ Authorization: `Bearer ${token}` }} />
        )}

       </main>
       <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} headers={{ Authorization: `Bearer ${token}` }} />
     </div>
   );
}
