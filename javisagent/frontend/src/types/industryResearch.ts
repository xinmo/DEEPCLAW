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

export interface GraphCompany {
  name: string;
  country?: string;
  marketShare?: number;
  exchange?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  layer?: string;
  companies: GraphCompany[];
  competitionType: "domestic" | "foreign" | "balanced" | string;
  nationalizationRate?: number;
  status: "pending" | "in_progress" | "done";
  overview?: string;
  upstreamDeps?: string[];
  latestNews?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}
