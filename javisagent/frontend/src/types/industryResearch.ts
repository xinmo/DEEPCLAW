export interface AgentStatus {
  agentId: string;
  name: string;
  status: "running" | "waiting" | "done";
  action?: string;
  detail?: string;
}

export interface LogEntry {
  timestamp: string;
  message: string;
}

export interface GraphNode {
  id: string;
  label: string;
  companies: string[];
  competitionType: "domestic" | "foreign" | "balanced" | string;
  status: "pending" | "in_progress" | "done";
}

export interface GraphEdge {
  source: string;
  target: string;
}
