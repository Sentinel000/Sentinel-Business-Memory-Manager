'use client';

import React, { useState } from 'react';
import { useCompanyStore } from '@/stores/useCompanyStore';
import { Employee } from '@/types';
import { Plus, UserCheck, KeyRound, Trash2 } from 'lucide-react';
import { apiErrorMessage } from '@/lib/api';

export const EmployeeRosterTable: React.FC = () => {
  const { employees, createEmployee, deleteEmployee, provisionLogin, bulkImportEmployees } = useCompanyStore();
  const [showAdd, setShowAdd] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [name, setName] = useState('');
  const [title, setTitle] = useState('');
  const [bulkText, setBulkText] = useState('');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [provisionId, setProvisionId] = useState<string | null>(null);
  const [provisionError, setProvisionError] = useState('');
  const [busy, setBusy] = useState(false);

  // manager_id is what the API returns; the name is resolved from the roster
  // already in memory rather than asking the server for it.
  const nameById = new Map(employees.map((e) => [e.id, e.name]));

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await createEmployee({ name, role_title: title });
    setName('');
    setTitle('');
    setShowAdd(false);
  };

  const handleBulk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bulkText.trim()) return;
    await bulkImportEmployees(bulkText);
    setBulkText('');
    setShowBulk(false);
  };

  const handleProvision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!provisionId || !loginEmail.trim()) return;
    setProvisionError('');
    setBusy(true);
    try {
      await provisionLogin(provisionId, loginEmail, loginPassword);
      setProvisionId(null);
      setLoginEmail('');
      setLoginPassword('');
    } catch (err) {
      setProvisionError(apiErrorMessage(err, 'Could not create that login.'));
    } finally {
      setBusy(false);
    }
  };

  const closeProvision = () => {
    setProvisionId(null);
    setLoginEmail('');
    setLoginPassword('');
    setProvisionError('');
  };

  return (
    <div className="stone-card p-4 sm:p-6 space-y-5 bg-white">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-stone-border pb-4">
        <div className="space-y-1">
          <h3 className="font-semibold text-ink-black text-base">Employee Roster & Access</h3>
          <p className="text-xs text-warm-gray">Manage team hierarchy and dashboard credentials</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowBulk(!showBulk)} className="btn-ghost text-xs py-1.5 px-3">
            Bulk Import
          </button>
          <button onClick={() => setShowAdd(!showAdd)} className="btn-cyan text-xs py-1.5 px-3 flex items-center gap-1">
            <Plus className="w-3.5 h-3.5" /> Add Employee
          </button>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={handleCreate} className="p-4 bg-stone-canvas border border-stone-border rounded-lg flex flex-col sm:flex-row gap-3 text-xs">
          <input
            type="text"
            placeholder="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 p-2 border border-stone-border rounded bg-white"
          />
          <input
            type="text"
            placeholder="Title (e.g. Lead Designer)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="flex-1 p-2 border border-stone-border rounded bg-white"
          />
          <button type="submit" className="btn-cyan text-xs px-4">Save</button>
        </form>
      )}

      {showBulk && (
        <form onSubmit={handleBulk} className="p-4 bg-stone-canvas border border-stone-border rounded-lg space-y-3 text-xs">
          <span className="font-medium text-ink-black block">Paste lines (Format: Name, Title, Manager Name):</span>
          <textarea
            rows={3}
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            placeholder="Sarah Jenkins, Product Lead, Alex Rivers&#10;Mark Twin, Backend Dev, Alex Rivers"
            className="w-full p-2 border border-stone-border rounded bg-white font-mono"
          />
          <button type="submit" className="btn-cyan text-xs px-4">Import Roster</button>
        </form>
      )}

      {/* Roster Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-stone-canvas border-b border-stone-border text-warm-gray uppercase text-[10px] tracking-wider">
            <tr>
              <th className="p-3">Employee Name</th>
              <th className="p-3">Title</th>
              <th className="p-3">Manager</th>
              <th className="p-3">Portal Login</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-border text-ink-black font-medium">
            {employees.map((emp) => (
              <tr key={emp.id} className="hover:bg-stone-canvas/50">
                <td className="p-3 font-semibold">{emp.name}</td>
                <td className="p-3 text-warm-gray">{emp.role_title || 'Team Member'}</td>
                <td className="p-3 text-warm-gray">
                  {(emp.manager_id && nameById.get(emp.manager_id)) || 'Self / Founder'}
                </td>
                <td className="p-3">
                  {emp.has_login ? (
                    <span className="px-2 py-0.5 text-[10px] bg-sky-wash text-cyan-edge rounded-full flex items-center gap-1 w-fit">
                      <UserCheck className="w-3 h-3" /> Active Credentials
                    </span>
                  ) : (
                    <button
                      onClick={() => setProvisionId(emp.id)}
                      className="text-cyan-edge hover:underline font-medium flex items-center gap-1"
                    >
                      <KeyRound className="w-3.5 h-3.5" /> Create Login
                    </button>
                  )}
                </td>
                <td className="p-3 text-right">
                  <button onClick={() => deleteEmployee(emp.id)} className="text-rose-600 hover:text-rose-800 p-1">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Login Provision Modal */}
      {provisionId && (
        <form onSubmit={handleProvision} className="p-4 bg-sky-wash/40 border border-cyan-edge/30 rounded-lg space-y-3 text-xs">
          <div className="space-y-0.5">
            <span className="font-semibold text-ink-black block">Provision Employee Credentials</span>
            <span className="text-warm-gray block">
              Creating a login for {employees.find((e) => e.id === provisionId)?.name}. Share the
              password with them directly.
            </span>
          </div>

          {provisionError && (
            <div className="p-2 bg-rose-50 border border-rose-200 rounded text-rose-700 font-medium">
              {provisionError}
            </div>
          )}

          <input
            type="email"
            required
            placeholder="Employee Email Address"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full p-2 border border-stone-border rounded bg-white"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Temporary Password (min 8 characters)"
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            className="w-full p-2 border border-stone-border rounded bg-white"
          />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={closeProvision} className="btn-ghost text-xs py-1 px-3">Cancel</button>
            <button type="submit" disabled={busy} className="btn-cyan text-xs py-1 px-4 disabled:opacity-60">
              {busy ? 'Creating…' : 'Generate Account'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
