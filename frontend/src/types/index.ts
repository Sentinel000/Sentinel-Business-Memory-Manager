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
  persona_instructions?: string | null;
  escalation_window_hours?: number;
  slack_bot_configured?: boolean;
  auto_approve_threshold: number;
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
