export type ToolCall = {
  id?: string;
  name?: string;
  arguments?: unknown;
  args?: unknown;
};

export type ToolResult = {
  call_id?: string;
  name?: string;
  tool?: string;
  ok?: boolean;
  result?: unknown;
  error?: string;
};

export type Round = {
  round_index?: number;
  round?: number;
  stage?: string;
  assistant_text?: string | null;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
};

export type ToolEvent = {
  name?: string;
  tool?: string;
  ok?: boolean;
  args?: unknown;
  result?: unknown;
  error?: string;
};

export type Evidence = {
  tool?: string;
  title?: string;
  url?: string;
  source?: string;
  published_at?: string;
  snippet?: string;
  summary?: string;
  published_date?: string;
  backend?: string;
};

export type ChatTurn = {
  turn_index?: number;
  user: string;
  assistant_text?: string | null;
  status?: string;
  error?: string;
  rounds?: Round[];
  tool_events?: ToolEvent[];
  evidence?: Evidence[];
};

export type EvalRun = {
  run_id?: string;
  artifact_version?: string;
  summary?: Record<string, number | string | boolean | null>;
};

export type AppMeta = {
  name?: string;
  version?: string;
  provider?: string;
  model?: string;
  artifact?: Record<string, string>;
  evals?: { base?: EvalRun | null; group?: EvalRun | null };
};

export type ChatResponse = {
  session_id: string;
  turn: ChatTurn;
  artifact?: Record<string, string>;
};
