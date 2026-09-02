'use client';

import React, { useEffect, useState } from 'react';
import { useTasksStore } from '@/stores/useTasksStore';
import { useCompanyStore } from '@/stores/useCompanyStore';
import { TaskCard, TaskDetailModal } from '@/components/tasks';
import { Task, Employee } from '@/types';
import { Plus } from 'lucide-react';

export default function TasksPage() {
  const { tasks, fetchTasks, createTask, updateTaskStatus, deleteTask, statusFilter, setStatusFilter, ownerFilter, setOwnerFilter } = useTasksStore();
  const { employees, fetchEmployees } = useCompanyStore();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [deadline, setDeadline] = useState('');

  useEffect(() => {
    fetchTasks();
    fetchEmployees();
  }, [fetchTasks, fetchEmployees]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await createTask({ title, owner_id: ownerId || undefined, deadline: deadline || undefined });
    setTitle('');
    setShowCreate(false);
  };

  return (
    <div className="space-y-6">
      <div className="stone-card p-6 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Operational <span className="cyan-highlight">Task Ledger</span>
          </h1>
          <p className="text-xs text-warm-gray">Active commitments, assigned owners, and deadline timelines across the company</p>
        </div>

        <button onClick={() => setShowCreate(!showCreate)} className="btn-cyan text-xs px-4 py-2 flex items-center gap-1.5 w-fit">
          <Plus className="w-4 h-4" /> Add Manual Commitment
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreateSubmit} className="stone-card p-5 bg-white space-y-4 border-cyan-edge/40">
          <h3 className="text-sm font-semibold text-ink-black">Create Manual Commitment (Auto-Approved)</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <input
              type="text"
              required
              placeholder="Commitment Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="p-2 border border-stone-border rounded"
            />
            <select value={ownerId} onChange={(e) => setOwnerId(e.target.value)} className="p-2 border border-stone-border rounded bg-white">
              <option value="">Select Assignee</option>
              {employees.map((emp: Employee) => (
                <option key={emp.id} value={emp.id}>{emp.name}</option>
              ))}
            </select>
            <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} className="p-2 border border-stone-border rounded" />
          </div>
          <div className="flex justify-end gap-2 text-xs">
            <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost py-1 px-3">Cancel</button>
            <button type="submit" className="btn-cyan py-1 px-4">Create Task</button>
          </div>
        </form>
      )}

      <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center text-xs">
        <div className="flex gap-1 bg-white p-1 rounded-full border border-stone-border overflow-x-auto max-w-full">
          {['all', 'in_progress', 'blocked', 'done'].map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`px-3 py-1 rounded-full font-medium capitalize transition ${
                statusFilter === f ? 'bg-inverse text-white shadow-subtle' : 'text-warm-gray hover:text-ink-black'
              }`}
            >
              {f === 'all' ? 'All Tasks' : f.replace('_', ' ')}
            </button>
          ))}
        </div>

        <select
          value={ownerFilter}
          onChange={(e) => setOwnerFilter(e.target.value)}
          className="p-1.5 border border-stone-border rounded bg-white text-xs font-medium text-ink-black"
        >
          <option value="all">All Assignees</option>
          {employees.map((emp: Employee) => (
            <option key={emp.id} value={emp.id}>{emp.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tasks.map((task: Task) => (
          <TaskCard key={task.id} task={task} onSelect={setSelectedTask} />
        ))}
      </div>

      <TaskDetailModal
        task={selectedTask}
        onClose={() => setSelectedTask(null)}
        onUpdateStatus={updateTaskStatus}
        onDelete={deleteTask}
      />
    </div>
  );
}
