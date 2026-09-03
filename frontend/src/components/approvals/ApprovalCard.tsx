'use client';

import React, { useState } from 'react';
import { ApprovalItem, Employee } from '@/types';
import { Check, X, Edit2, Quote, Clock, Wand2 } from 'lucide-react';

interface Props {
  item: ApprovalItem;
  employees: Employee[];
  onApprove: (id: string) => void;
  onReject: (id: string, reason?: string) => void;
  onEdit: (id: string, payload: any) => void;
}

export const ApprovalCard: React.FC<Props> = ({ item, employees, onApprove, onReject, onEdit }) => {
  const [showQuote, setShowQuote] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(item.title);
  const [editOwner, setEditOwner] = useState(item.owner_id || '');
  const [editDeadline, setEditDeadline] = useState(item.deadline?.split('T')[0] || '');

  const handleSaveEdit = () => {
    onEdit(item.id, {
      title: editTitle,
      owner_id: editOwner || undefined,
      deadline: editDeadline || undefined,
    });
    setIsEditing(false);
  };

  return (
    <div className="stone-card p-5 space-y-4 hover:border-cyan-edge/40 transition">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1.5 flex-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-[11px] font-semibold bg-sky-wash text-cyan-edge rounded-full">
              Extracted Action Item
            </span>
            {item.confidence_score && (
              <span className="text-xs text-warm-gray flex items-center gap-1">
                <Wand2 className="w-3 h-3 text-cyan-signal" />
                {(item.confidence_score * 100).toFixed(0)}% confidence
              </span>
            )}
          </div>

          {isEditing ? (
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full text-base font-semibold text-ink-black border border-stone-border p-1.5 rounded"
            />
          ) : (
            <h3 className="text-base font-semibold text-ink-black leading-snug">{item.title}</h3>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {isEditing ? (
            <button onClick={handleSaveEdit} className="btn-cyan text-xs py-1 px-3">
              Save Edit
            </button>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded"
              title="Edit Task"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Metadata Assignee & Deadline Pill Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-stone-canvas p-3 rounded-lg border border-stone-border/60">
        <div className="flex items-center gap-2">
          <span className="text-warm-gray font-medium w-16">Assignee:</span>
          {isEditing ? (
            <select
              value={editOwner}
              onChange={(e) => setEditOwner(e.target.value)}
              className="p-1 border border-stone-border rounded bg-white"
            >
              <option value="">Unassigned</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name} ({emp.role_title || 'Team Member'})
                </option>
              ))}
            </select>
          ) : (
            <span className="font-semibold text-ink-black">{item.owner_name || 'Unassigned'}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-warm-gray font-medium w-16">Deadline:</span>
          {isEditing ? (
            <input
              type="date"
              value={editDeadline}
              onChange={(e) => setEditDeadline(e.target.value)}
              className="p-1 border border-stone-border rounded bg-white"
            />
          ) : (
            <span className="font-semibold text-ink-black flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-warm-gray" />
              {item.deadline ? new Date(item.deadline).toLocaleDateString() : 'No deadline'}
            </span>
          )}
        </div>
      </div>

      {/* Verbatim Source Quote Accordion */}
      {item.source_quote && (
        <div className="space-y-1.5">
          <button
            onClick={() => setShowQuote(!showQuote)}
            className="text-xs text-cyan-edge font-medium flex items-center gap-1 hover:underline"
          >
            <Quote className="w-3.5 h-3.5" />
            <span>{showQuote ? 'Hide source quote' : 'View verbatim source quote'}</span>
          </button>

          {showQuote && (
            <blockquote className="p-3 bg-stone-canvas border-l-2 border-cyan-signal text-xs text-warm-gray italic rounded-r-lg">
              &quot;{item.source_quote}&quot;
            </blockquote>
          )}
        </div>
      )}

      {/* Action Buttons Bar */}
      <div className="pt-2 flex items-center justify-between border-t border-stone-border">
        <span className="text-xs text-warm-gray font-mono">{item.source_ref || 'Extracted via Sentinel'}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onReject(item.id)}
            className="btn-ghost text-xs py-1.5 px-3.5 text-rose-600 hover:bg-rose-50 border-stone-border flex items-center gap-1"
          >
            <X className="w-3.5 h-3.5" />
            <span>Reject</span>
          </button>
          <button
            onClick={() => onApprove(item.id)}
            className="btn-cyan text-xs py-1.5 px-4 flex items-center gap-1 shadow-subtle"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Approve & Delegate</span>
          </button>
        </div>
      </div>
    </div>
  );
};
