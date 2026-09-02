'use client';

import React, { useEffect } from 'react';
import { useTasksStore } from '@/stores/useTasksStore';
import { useCompanyStore } from '@/stores/useCompanyStore';
import { ApprovalCard } from '@/components/approvals';
import { ApprovalItem } from '@/types';
import { CheckSquare } from 'lucide-react';
import { BrandMark } from '@/components/ui';

export default function ApprovalsPage() {
  const { approvals, fetchApprovals, approveTask, rejectTask, editApproval, bulkApprove } = useTasksStore();
  const { employees, fetchEmployees } = useCompanyStore();

  useEffect(() => {
    fetchApprovals();
    fetchEmployees();
  }, [fetchApprovals, fetchEmployees]);

  const handleBulk = () => {
    const ids = approvals.map((a: ApprovalItem) => a.id);
    if (ids.length > 0) bulkApprove(ids);
  };

  return (
    <div className="space-y-6">
      <div className="stone-card p-6 bg-white flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Founder <span className="cyan-highlight">Approval Queue</span>
          </h1>
          <p className="text-xs text-warm-gray">
            Review and delegate commitments extracted by Sentinel from meetings and communication threads.
          </p>
        </div>

        {approvals.length > 0 && (
          <button onClick={handleBulk} className="btn-cyan text-xs px-5 py-2.5 flex items-center gap-2">
            <CheckSquare className="w-4 h-4" /> Approve All ({approvals.length})
          </button>
        )}
      </div>

      {approvals.length === 0 ? (
        <div className="stone-card p-12 text-center space-y-3 bg-white">
          <div className="w-12 h-12 bg-sky-wash text-cyan-signal rounded-full flex items-center justify-center mx-auto">
            <BrandMark className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-ink-black">Queue Cleared</h3>
          <p className="text-xs text-warm-gray max-w-sm mx-auto">
            All extracted commitments have been reviewed. Sentinel is listening for new meeting recordings and status updates.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((item: ApprovalItem) => (
            <ApprovalCard
              key={item.id}
              item={item}
              employees={employees}
              onApprove={approveTask}
              onReject={rejectTask}
              onEdit={editApproval}
            />
          ))}
        </div>
      )}
    </div>
  );
}
