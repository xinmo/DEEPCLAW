export type ResearchDepth = "quick" | "standard" | "deep";
export type ResearchView = "home" | "dashboard" | "graph" | "deep";
export type ResearchStatus = "running" | "completed" | "failed";

export interface ResearchHistory {
  id: string;
  query: string;
  depth: ResearchDepth;
  status: ResearchStatus;
  createdAt: string;
  updatedAt?: string;
  nodeCount?: number;
  companyCount?: number;
  progress?: number;
}

export interface SSEEvent {
  type:
    | "agent_status"
    | "log"
    | "graph_node"
    | "graph_edge"
    | "progress"
    | "report_chunk"
    | "deep_data"
    | "done"
    | "error";
  data: Record<string, unknown>;
}

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

export interface CompanyFinancial {
  name: string;
  ticker: string;
  revenue: number;
  grossMargin: number;
  pe: number;
  domesticContribution: number;
}

export interface MarketShare {
  name: string;
  country: string;
  share: number;
}

export interface PricePoint {
  date: string;
  value: number;
}

export interface Material {
  name: string;
  analysis?: string;
  priceHistory?: PricePoint[];
}

export interface BarrierItem {
  dimension: string;
  score: number;
}

export interface RiskItem {
  level: "high" | "medium" | "low";
  title: string;
  description: string;
}

export interface DeepResearchData {
  marketShares: MarketShare[];
  companies: CompanyFinancial[];
  materials: Material[];
  barriers: BarrierItem[];
  risks: RiskItem[];
  materialAnalysis?: string;
}
