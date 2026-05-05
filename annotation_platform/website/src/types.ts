// --- Summary types (loaded from summary.json, ~1.2 MB) ---

export interface DetectorStats {
  name: string;
  total: number;
  passed: number;
  failed: number;
  avg_score: number;
}

export interface ConditionStats {
  condition: string;
  total: number;
  passed: number;
  failed: number;
  asr: number;
  adj_total: number;
  adj_failed: number;
  adj_asr: number;
  false_positives: number;
  reviewed: number;
  total_cost: number;
  target_cost: number;
  attacker_cost: number;
  cost_per_attack: number;
  target_tokens: number;
  attacker_tokens: number;
}

export interface FailureTypeDistribution {
  condition: string;
  detector_failures: Record<string, number>;
  detector_failures_all: Record<string, number>;
}

export interface DetectorConditionStats {
  total: number;
  passed: number;
  failed: number;
  fail_rate: number;
  avg_score: number;
  reviewed: number;
  confirmed: number;
  judge_errors: number;
  accuracy: number;
  error_rate: number;
}

export interface DetectorByCondition {
  detector: string;
  by_condition: Record<string, DetectorConditionStats>;
}

export interface CascadeConditionCard {
  total: number;
  refusal_rate: number;
  asr: number;
  judge_agreement_rate: number;
  awcs: number;
  severity_distribution: Record<string, number>;
  critical_damage_rate: number;
}

export interface CascadeCard {
  awcs: number;
  refusal_rate: number;
  judge_agreement_rate: number;
  severity_distribution: Record<string, number>;
  critical_damage_rate: number;
  error_count: number;
  error_rate: number;
  total_findings: number;
  unreviewed: number;
  per_condition: Record<string, CascadeConditionCard>;
  per_condition_model: Record<string, Record<string, CascadeConditionCard>>;
  per_model: Record<string, CascadeConditionCard>;
  parameters: { alpha: number; gamma: number; lambda: number };
}

export interface Summary {
  experiment: ExperimentInfo;
  scans: ScanSummary[];
  probes: ProbeSummary[];
  findings_index: FindingIndex[];
  compliance: ComplianceEntry[];
  detector_stats: DetectorStats[];
  condition_stats: ConditionStats[];
  failure_type_distribution: FailureTypeDistribution[];
  detector_by_condition: DetectorByCondition[];
  cascade_card?: CascadeCard;
}

export interface ExperimentInfo {
  id: string;
  timestamp: string;
  models: string[];
  conditions: string[];
}

export interface ProbeResultSummary {
  probe_name: string;
  category: string;
  total_attempts: number;
  passed: number;
  failed: number;
  pass_rate: number;
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
  article_details: ArticleDetail[];
}

export interface ArticleDetail {
  article_id: string;
  title: string;
  status: string;
  findings_count: number;
  critical_findings: number;
  risk_score: number;
}

export interface ScanSummary {
  model: string;
  model_short: string;
  scan_id: string;
  probe: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  total_cost_usd: number;
  total_target_cost_usd: number;
  total_attacker_cost_usd: number;
  total_target_tokens: number;
  total_attacker_tokens: number;
  security_score: SecurityScore;
  compliance_assessment: ComplianceAssessment;
  recommendations: string[];
  probe_results_summary: Record<string, ProbeResultSummary>;
}

export interface ProbeSummary {
  probe_name: string;
  total_attempts: number;
  passed: number;
  failed: number;
  models: Record<string, {
    pass_rate: number;
    passed: number;
    failed: number;
    total_attempts: number;
  }>;
}

export interface DetectorSummaryEntry {
  name: string;
  passed: boolean;
  score: number;
}

export interface FindingIndex {
  id: string;
  model: string;
  model_short: string;
  probe: string;
  passed: boolean;
  severity: string;
  prompt_preview: string;
  condition: string;
  adaptivity: string;
  interaction_mode: string;
  num_messages: number;
  num_target_calls: number;
  num_attacker_calls: number;
  cost_usd: number;
  latency_ms: number;
  target_tokens: number;
  attacker_tokens: number;
  detector_summary: DetectorSummaryEntry[];
}

export interface ComplianceEntry {
  model: string;
  model_short: string;
  article_id: string;
  title: string;
  status: string;
  findings_count: number;
  critical_findings: number;
  risk_score: number;
}

// --- Full finding detail (loaded on-demand per finding) ---

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
  messages: Array<{ role: string; content: string }>;
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

export interface FindingDetail {
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

// --- Aggregated types for dashboard ---

export interface ModelAggregation {
  model: string;
  modelShort: string;
  probes: Record<string, ProbeResultSummary>;
  overallPassRate: number;
  totalAttempts: number;
  totalPassed: number;
  totalFailed: number;
  totalCost: number;
  totalTargetCost: number;
  totalAttackerCost: number;
  totalTokens: number;
  avgLatency: number;
  riskLevel: string;
  complianceStatus: string;
  securityScore: number;
}
