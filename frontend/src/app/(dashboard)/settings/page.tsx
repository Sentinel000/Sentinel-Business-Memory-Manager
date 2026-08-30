'use client';

import React, { useEffect } from 'react';
import { useCompanyStore } from '@/stores/useCompanyStore';
import { EmployeeRosterTable } from '@/components/EmployeeRosterTable';
import { PersonaConfigForm } from '@/components/PersonaConfigForm';

export default function SettingsPage() {
  const { fetchCompany, fetchEmployees } = useCompanyStore();

  useEffect(() => {
    fetchCompany();
    fetchEmployees();
  }, [fetchCompany, fetchEmployees]);

  return (
    <div className="space-y-6">
      <div className="stone-card p-6 bg-white space-y-1">
        <h1 className="text-2xl font-normal text-ink-black tracking-tight">
          Company & <span className="cyan-highlight">Team Settings</span>
        </h1>
        <p className="text-xs text-warm-gray">Configure Sentinel instructions, escalation parameters, and employee roster mapping</p>
      </div>

      <PersonaConfigForm />
      <EmployeeRosterTable />
    </div>
  );
}
