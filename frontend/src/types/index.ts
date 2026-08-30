export type Role = 'FOUNDER' | 'EMPLOYEE';
export type TaskStatus = 'PENDING_APPROVAL' | 'APPROVED' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED' | 'REJECTED';

export interface User {
  id: string;
  email: string;
  role: Role;
  company_id: string;
  employee_id?: string | null;
}

export interface Employee {
  id: string;
  company_id: string;
  name: string;
  title?: string | null;
  slack_user_id?: string | null;
  manager_id?: string | null;
  manager_name?: string | null;
  has_login?: boolean;
}

export interface Task {
  id: string;
  company_id: string;
  title: string;
  description?: string | null;
  status: TaskStatus;
  owner_id?: string | null;
  owner_name?: string | null;
  deadline?: string | null;
  days_late: number;
  source_type: string;
  source_ref?: string | null;
  source_quote?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalItem extends Task {
  confidence_score?: number;
  decider_name?: string | null;
}

export interface TranscriptSegment {
  id: string;
  meeting_id: string;
  speaker_label: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface Meeting {
  id: string;
  company_id: string;
  title: string;
  recorded_at: string;
  duration_seconds?: number | null;
  audio_filename?: string | null;
  audio_format?: string | null;
  raw_transcript?: string | null;
  status: 'pending' | 'transcribing' | 'extracting' | 'completed' | 'failed';
  error_message?: string | null;
  segments?: TranscriptSegment[];
  extracted_tasks?: Partial<Task>[];
}

export interface Company {
  id: string;
  name: string;
  persona_instructions?: string | null;
  escalation_window_hours?: number;
  slack_bot_configured?: boolean;
  auto_approve_threshold: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  content: string;
  timestamp: string;
  tool_executions?: Array<{ tool: string; status: string }>;
}
