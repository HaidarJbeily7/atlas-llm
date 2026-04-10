export interface ExperimentMeta {
  timestamp: string;
  models: string[];
  conditions: string[];
  all_detectors: boolean;
}

export interface Manifest {
  experiments: ExperimentEntry[];
}

export interface ExperimentEntry {
  id: string;
  timestamp: string;
  models: string[];
  conditions: string[];
  scans: ScanRef[];
}

export interface ScanRef {
  model_dir: string;
  probe: string;
  file: string;
}

export interface DetectorResult {
  detector_name: string;
  passed: boolean;
  score: number;
  confidence: number;
  evidence: string;
  needs_human_review: boolean;
  failure_type: string;
  judge_reasoning: string;
  judge_model: string;
  judge_tokens_in: number;
  judge_tokens_out: number;
  judge_cost_usd: number;
  judge_latency_ms: number;
  dimension_scores: Record<string, string>;
  matched_patterns: string[];
}

export interface Attempt {
  id: string;
  probe_name: string;
  prompt: string;
  response: string;
  system_prompt: string;
  messages: unknown[];
  metadata: Record<string, unknown>;
  tags: string[];
  timestamp: string;
  target_tokens_in: number;
  target_tokens_out: number;
  attacker_tokens_in: number;
  attacker_tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  num_target_calls: number;
  num_attacker_calls: number;
}

export interface Finding {
  id: string;
  attempt: Attempt;
  detector_results: DetectorResult[];
  severity: string;
  category: string;
  passed: boolean;
  needs_human_review: boolean;
  compliance_articles: string[];
  owasp_categories: string[];
}

export interface ProbeResult {
  probe_name: string;
  category: string;
  total_attempts: number;
  passed: number;
  failed: number;
  pass_rate: number;
  findings: Finding[];
}

export interface SecurityScore {
  overall_score: number;
  category_scores: Record<string, number>;
  risk_level: string;
  vulnerabilities_by_severity: Record<string, number>;
}

export interface ComplianceAssessment {
  overall_status: string;
  articles_assessed: number;
  articles_passed: number;
  articles_failed: number;
  high_risk_areas: string[];
  article_details: Array<{
    article_id: string;
    title: string;
    status: string;
    findings_count: number;
    critical_findings: number;
    risk_score: number;
  }>;
}

export interface ScanResult {
  scan_id: string;
  model_name: string;
  provider: string;
  profile: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  probe_results: Record<string, ProbeResult>;
  security_score: SecurityScore;
  compliance_assessment: ComplianceAssessment;
  recommendations: string[];
  total_cost_usd: number;
  total_target_tokens: number;
  total_attacker_tokens: number;
}

// Aggregated types for dashboard
export interface ModelSummary {
  model: string;
  modelShort: string;
  probes: Record<string, ProbeResult>;
  overallPassRate: number;
  totalAttempts: number;
  totalPassed: number;
  totalFailed: number;
  totalCost: number;
  totalTokens: number;
  avgLatency: number;
  riskLevel: string;
  complianceStatus: string;
  securityScore: number;
}
