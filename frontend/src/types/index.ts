export type Role = 'founder' | 'employee';
export type TaskStatus =
  | 'pending_approval'
  | 'approved'
  | 'in_progress'
  | 'blocked'
  | 'done'
  | 'rejected'
  | 'overdue';

export interface CompanySummary {
  id: string;
  name: string;
  industry?: string | null;
  persona_config?: {
    assistant_name?: string;
    tone?: string;
    company_context?: string;
    glossary?: Record<string, string>;
  };
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  role: Role;
  company_id: string;
  employee_id?: string | null;
  company: CompanySummary;
}

export interface Employee {
  id: string;
  company_id?: string;
  name: string;
  /** The backend field is role_title — not title. */
  role_title?: string | null;
  slack_user_id?: string | null;
  manager_id?: string | null;
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
  industry?: string | null;
  persona_config?: {
    assistant_name?: string;
    tone?: string;
    company_context?: string;
    glossary?: Record<string, string>;
  };
  /** Days of silence tolerated before a reminder, and the gap between reminders. */
  escalation_after_days: number;
  /** Reminders sent before a task stops being chased and is handed to the founder. */
  max_chases: number;
  /** Confidence at or above which an extracted task skips the approval queue. */
  auto_approve_threshold: number;
  slack_connected?: boolean;
  slack_team_id?: string | null;
  knowledge_connected?: boolean;
}

/** One tool call the agent made, as returned by the chat API. */
/** A task as a tool returns it — the summary subset, not the full Task row. */
export interface ToolTaskSummary {
  id: string;
  title: string;
  status: TaskStatus;
  deadline?: string | null;
  owner_employee_id?: string | null;
  owner_name?: string | null;
  days_late?: number | null;
}

export interface ToolExecution {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  result: string;
  ok: boolean;
  truncated: boolean;
  /**
   * Set by the tool on its success path. Selects the renderer; an error return
   * carries none and falls back to the raw JSON view.
   */
  kind?: string | null;
  /** The untruncated payload. `result` is capped for the agent, not the browser. */
  data?: unknown;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  content: string;
  timestamp: string;
  tool_executions?: ToolExecution[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/** What deleting a meeting would remove. `fact_count` is null when unknown. */
export interface MeetingDeletePreview {
  meeting_id: string;
  title: string;
  fact_count: number | null;
  task_count: number;
  title_is_ambiguous: boolean;
}

/** Why the graph believes a relation exists — the citation behind an edge. */
export interface GraphEvidence {
  predicate: string;
  context: string | null;
  timestamp: string | null;
  chunk_id: string | null;
}

export interface GraphNode {
  id: string;
  name: string;
  /** Lower-cased server-side: person, organization, concept, document, knowledge. */
  type: string;
  provider: string | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  predicate: string;
  evidence: GraphEvidence[];
  /**
   * An "authored"-style relation describing how a fact reached us rather than what
   * the company knows. Hidden by default — see the store's `showProvenance`.
   */
  is_provenance: boolean;
}

/**
 * `available: false` means memory is unconfigured or unreachable — distinct from an
 * empty graph, which is a real answer. `fact_count` disambiguates an empty graph:
 * rows with no edges means indexing is still building.
 */
export interface KnowledgeGraph {
  available: boolean;
  note: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
  fact_count: number | null;
}

/** One row in a briefing section. Loosely typed because sections differ. */
export interface ReportItem {
  task_id: string;
  title: string;
  owner: string | null;
  status: string;
  deadline: string | null;
  overdue_days: number | null;
  chase_count: number;
  source_quote: string | null;
  source_ref: string | null;
  /** needs_decision only — why this is waiting on the founder. */
  reason?: string;
  /** moved only. */
  moved_to?: string;
  note?: string | null;
  /** quiet only. */
  days_silent?: number | null;
  chases?: string;
}

export interface ReportSection {
  key: 'needs_decision' | 'slipping' | 'moved' | 'quiet';
  title: string;
  /** Shown when items is empty. "Nothing slipped" is a real answer, not a blank. */
  empty: string;
  items: ReportItem[];
  total: number;
  /** Matches beyond the display cap. */
  hidden: number;
}

export interface Report {
  id: string;
  /** The day described. */
  report_date: string;
  /** When it was last rebuilt — distinct from report_date. */
  generated_at: string;
  counts: Record<string, number>;
  sections: ReportSection[];
}

export interface ReportSummary {
  id: string;
  report_date: string;
  generated_at: string;
  counts: Record<string, number>;
}

/** A nudge Sentinel sent, shown to the employee it was aimed at. */
export interface Reminder {
  id: string;
  task_id: string;
  task_title: string;
  note: string | null;
  deadline: string | null;
  created_at: string;
  /** Whether the owner has replied since. Answered ones stay as history but
   *  stop counting toward the badge. */
  answered: boolean;
}
