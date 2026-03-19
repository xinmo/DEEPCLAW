export type ResearchDepth = 'quick' | 'standard' | 'deep';
export type ResearchView = 'home' | 'dashboard' | 'graph' | 'deep';
export type AgentStatusType = 'running' | 'waiting' | 'done';
export type NodeStatus = 'done' | 'in_progress' | 'pending';
export type CompetitionType = 'domestic' | 'foreign' | 'balanced';

export interface AgentStatus {
  agentId: string;
  name: string;
  status: AgentStatusType;
  action?: string;
  detail?: string;
}

export interface LogEntry {
  timestamp: string;
  message: string;
}

export interface CompanyInfo {
  name: string;
  country: string;
  marketShare?: number;
  ticker?: string;
  exchange?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  layer: string;
  status: NodeStatus;
  competitionType: CompetitionType;
  nationalizationRate?: number;
  companies: CompanyInfo[];
  overview?: string;
  upstreamDeps?: string[];
  latestNews?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface ResearchHistory {
  id: string;
  query: string;
  depth: ResearchDepth;
  status: 'running' | 'completed' | 'failed';
  progress?: number;
  nodeCount?: number;
  companyCount?: number;
  createdAt: string;
  updatedAt: string;
}

export interface MarketShareData {
  name: string;
  share: number;
  country: string;
}

export interface CompanyFinancial {
  name: string;
  ticker: string;
  revenue: number;
  grossMargin: number;
  pe: number;
  domesticContribution: number;
}

export interface MaterialPrice {
  name: string;
  data: { date: string; price: number }[];
  analysis?: string;
}

export interface BarrierScore {
  dimension: string;
  score: number;
}

export interface RiskItem {
  level: 'high' | 'medium' | 'low';
  description: string;
}

export interface DeepResearchData {
  marketShares: MarketShareData[];
  companies: CompanyFinancial[];
  materials: MaterialPrice[];
  barriers: BarrierScore[];
  risks: RiskItem[];
}

// SSE event types
export type SSEEventType =
  | 'agent_status'
  | 'log'
  | 'graph_node'
  | 'graph_edge'
  | 'progress'
  | 'report_chunk'
  | 'deep_data'
  | 'done'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
}
