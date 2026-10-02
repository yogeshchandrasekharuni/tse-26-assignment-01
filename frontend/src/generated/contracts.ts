/* Generated from strict Python models by make contracts. Do not edit. */

export type AreaUnit = string
export type Label = string
export type Y = string
export type CountTicks = AxisTick[]
export type CsvUrl = string
export type JsonUrl = string
export type LastYoyLabel = string
export type MoneyUnit = string
export type CountMom = string
export type X = string
export type Y1 = string | null
export type Label1 = string
export type Month = string
export type Observations = string
export type PpsfMom = string
export type Price = string
export type PriceMom = string
export type PricePerArea = string
export type PriceYoy = string
export type ShortLabel = string
export type Support = 'empty' | 'sparse' | 'supported'
export type Months = MonthView[]
export type Origin = 'live_capture' | 'live' | 'replay'
/**
 * @minItems 12
 * @maxItems 12
 */
export type Monthly = [
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1,
  Monthly1
]
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Decimal6".
 */
export type Decimal6 = string
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "NonnegativeInt".
 */
export type NonnegativeInt = number
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Unsigned6".
 */
export type Unsigned6 = string
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Month".
 */
export type Month1 = string
/**
 * @maxItems 12
 */
export type ZipRankings =
  | []
  | [ZipRanking]
  | [ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking]
  | [ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking, ZipRanking]
  | [
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking
    ]
  | [
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking
    ]
  | [
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking,
      ZipRanking
    ]
export type Rank = number | null
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Zip".
 */
export type Zip =
  '75001' | '75006' | '75019' | '75024' | '75034' | '75038' | '75063' | '75080' | '75093' | '75201' | '75204' | '75214'
export type ContractVersion = '1.0'
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Identifier".
 */
export type Identifier = string
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Sha256".
 */
export type Sha256 = string
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Seed".
 */
export type Seed = number
export type LiveCampaignId = string | null
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Mode".
 */
export type Mode = 'live' | 'replay' | 'policy_simulation'
export type ModelProfile = string
export type SeedSupport = 'verified_model_default' | 'best_effort' | 'unsupported' | 'replay_recorded'
export type TracePath = string
export type CaveatCodes = string[]
export type FactIds = string[]
export type Text = string
export type Area = 'SQFT' | 'SQM'
export type Money = 'USD' | 'USD_THOUSANDS'
/**
 * @minItems 12
 * @maxItems 12
 */
export type Monthly2 = [
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth,
  PresentedMonth
]
export type Codes = string[]
export type SparseMonths = Month1[]
export type Status = 'complete' | 'limited'
export type Status1 = 'completed'
export type PpsfTicks = AxisTick[]
export type PriceTicks = AxisTick[]
export type Purpose = 'analysis' | 'development_smoke' | 'auxiliary_index_omission'
export type CompareRegions = boolean
export type BedroomsMax = number
export type BedroomsMin = number
/**
 * @minItems 1
 */
export type PropertyTypes = [PropertyType, ...PropertyType[]]
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "PropertyType".
 */
export type PropertyType = 'single_family' | 'condo' | 'townhouse'
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "PositiveInt".
 */
export type PositiveInt = number
/**
 * @minItems 1
 */
export type Zips = [Zip, ...Zip[]]
export type Area1 = 'SQFT' | 'SQM'
export type Money1 = 'USD' | 'USD_THOUSANDS'
export type TotalLabel = string
export type TraceUrl = string
export type WindowChangeLabel = string
export type Description = string
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CaptureId".
 */
export type CaptureId = 'normal' | 'feedback'
export type Purpose1 = 'development_smoke' | 'auxiliary_index_omission'
export type Title = string
export type Captures = CaptureSummary[]
export type ContractVersion1 = '1.0'
export type DataLicense = string
export type GeneratedAtUtc = string
export type Algorithm = string
export type ConfigPath = string
export type Path = string
export type PythonVersion = string
export type Limitations = string[]
export type PropertyTypes1 = PropertyType[]
export type SchemaVersion = '1.0'
export type SnapshotPath = string
export type SourceKind = 'synthetic' | 'synthetic_fixture' | 'transformed'
export type Zips1 = Zip[]
export type FastAgentVersion = string
export type LiveModelProfile = string
export type LiveModelRequirements = string
export type ComparedFields = string[]
export type Family = string
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "MRId".
 */
export type MRId = 'MR01' | 'MR02' | 'MR03' | 'MR04' | 'MR05' | 'MR06' | 'MR07' | 'MR08' | 'MR09' | 'MR10'
export type Preconditions = string[]
export type Relation = string
export type Title1 = string
export type Witness = string
export type MrCatalog = CatalogEntry[]
export type PythonVersion1 = string
export type SeedValues = number[]
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "JsonValue".
 */
export type JsonValue = unknown
export type BaseId = string
export type CampaignId = string
export type AbsoluteError = string | null
export type Path1 = string
export type Rule = string
export type Tolerance = string | null
export type Differences = Difference[]
export type MaxAbsoluteError = string
export type Status2 = 'pass' | 'violation'
export type EligibilityPath = string
export type CapturePath = string | null
export type EffectiveSeed = number | null
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "ErrorCode".
 */
export type ErrorCode =
  | 'DATA_INVALID'
  | 'DATA_INCOMPLETE'
  | 'AGENT_OUTPUT_INVALID'
  | 'AGENT_POLICY_ERROR'
  | 'BUDGET_EXCEEDED'
  | 'REPLAY_MISS'
  | 'TOOL_ERROR'
  | 'MODEL_UNAVAILABLE'
export type ErrorStage = string | null
export type RequestedSeed = number
export type RunId = string
export type RunPath = string
export type Status3 = 'completed' | 'failed'
export type LiveCampaignId1 = string
export type Mode1 = 'live' | 'replay'
export type MrVersion = '1.0'
export type ReasonCodes = ErrorCode[]
export type SchemaVersion1 = 'case-2'
export type Seed1 = number
export type SliceGroup = string
export type SourceReusedFrom = string | null
export type Status4 = 'pass' | 'violation' | 'execution_error'
export type ViolationKind = ('relation' | 'output_contract') | null
export type BaseId1 = string
export type Key = string
export type MrId = string
export type Seed2 = number
export type SourceReused = boolean
export type Status5 = string
export type ViolationKind1 = string | null
export type CaseIndex = CaseIndexItem[]
export type Code = string
export type Message = string
export type Stage = string
export type CohortPath = string
export type BaseRate = string | null
export type BaseRateLabel = string
export type CampaignId1 = string
export type Ci95High = string | null
export type Ci95Label = string
export type Ci95Low = string | null
export type CiMethod = 'wilson_score'
export type CiUnit = 'distinct_completed_eligible_base'
export type Complete = boolean
export type Family1 = 'invariance' | 'monotonic' | 'directional'
export type Interpretation = string
export type LiveCampaignId2 = string
export type Mode2 = 'live' | 'replay'
export type SchemaVersion2 = 'headline-2'
export type SeedValues1 = number[]
export type Headlines = HeadlineDisplay[]
export type Id = string
export type LastCase = string | null
export type LastStatus = string | null
export type Mode3 = 'live' | 'replay'
export type Scope = 'pilot' | 'headline' | 'auxiliary'
export type Seeds = number[]
export type State = 'running' | 'complete' | 'incomplete'
export type Campaigns = CampaignOverview[]
export type CreatedAtUtc = string
export type Id1 = string
export type State1 = 'queued' | 'running' | 'completed' | 'failed'
export type Mode4 = 'live' | 'replay'
export type UpdatedAtUtc = string
export type Dispatched = {
  [k: string]: JsonValue
} | null
export type Response = {
  [k: string]: JsonValue
} | null
export type Actor = string
export type Event = string
export type IllustrativeFixture = boolean
export type ParentEventSequence = number | null
export type RunId1 = string
export type SchemaVersion3 = '1.0'
export type TimestampUtc = string
export type Events = TraceEvent[]
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "EvidenceScope".
 */
export type EvidenceScope = 'analysis' | 'development_smoke' | 'auxiliary_index_omission' | 'pilot' | 'headline'
export type QueryUnchanged = boolean
export type RunId2 = string
export type Status6 = 'completed' | 'failed' | 'running'
export type TraceUrl1 = string

/**
 * Schema-generation envelope; endpoints return these members directly.
 */
export interface ClientContracts {
  analysis: AnalysisView
  bootstrap: Bootstrap
  case_detail: CaseDetail
  case_index: CaseIndex
  error: ErrorInfo
  experiments: ExperimentView
  job: Job
  model_turn: ModelTurn
  submission: Submission
  workflow: WorkflowView
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "AnalysisView".
 */
export interface AnalysisView {
  area_unit: AreaUnit
  count_ticks: CountTicks
  csv_url: CsvUrl
  json_url: JsonUrl
  last_yoy_label: LastYoyLabel
  money_unit: MoneyUnit
  months: Months
  origin: Origin
  output: AnalysisOutput
  ppsf_ticks: PpsfTicks
  price_ticks: PriceTicks
  purpose: Purpose
  request: AnalysisRequest
  total_label: TotalLabel
  trace_url: TraceUrl
  window_change_label: WindowChangeLabel
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "AxisTick".
 */
export interface AxisTick {
  label: Label
  y: Y
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "MonthView".
 */
export interface MonthView {
  count_mom: CountMom
  count_plot: PlotPoint
  label: Label1
  month: Month
  observations: Observations
  ppsf_mom: PpsfMom
  ppsf_plot: PlotPoint
  price: Price
  price_mom: PriceMom
  price_per_area: PricePerArea
  price_plot: PlotPoint
  price_yoy: PriceYoy
  short_label: ShortLabel
  support: Support
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "PlotPoint".
 */
export interface PlotPoint {
  x: X
  y: Y1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "AnalysisOutput".
 */
export interface AnalysisOutput {
  canonical: Canonical
  metadata: Metadata
  narrative: Narrative
  presentation: Presentation
  quality: Quality
  status: Status1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Canonical".
 */
export interface Canonical {
  monthly: Monthly
  summary: Summary
  window_end: Month1
  window_start: Month1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Monthly".
 */
export interface Monthly1 {
  count_mom_pct: Decimal6 | null
  listing_count: NonnegativeInt
  median_ppsf_usd: Unsigned6 | null
  median_price_usd: Unsigned6 | null
  month: Month1
  ppsf_mom_pct: Decimal6 | null
  ppsf_yoy_pct: Decimal6 | null
  price_mom_pct: Decimal6 | null
  price_yoy_pct: Decimal6 | null
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Summary".
 */
export interface Summary {
  last_month_ppsf_yoy_pct: Decimal6 | null
  last_month_price_yoy_pct: Decimal6 | null
  total_observations: NonnegativeInt
  window_ppsf_change_pct: Decimal6 | null
  window_price_change_pct: Decimal6 | null
  zip_rankings: ZipRankings
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "ZipRanking".
 */
export interface ZipRanking {
  median_ppsf_usd: Unsigned6 | null
  rank: Rank
  zip: Zip
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Metadata".
 */
export interface Metadata {
  contract_version: ContractVersion
  dataset_id: Identifier
  dataset_view_sha256: Sha256
  effective_seed: Seed | null
  live_campaign_id: LiveCampaignId
  logical_multiset_sha256: Sha256
  mode: Mode
  model_profile: ModelProfile
  prompt_bundle_sha256: Sha256
  query_sha256: Sha256
  requested_seed: Seed
  run_id: Identifier
  seed_support: SeedSupport
  snapshot_sha256: Sha256
  trace_path: TracePath
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Narrative".
 */
export interface Narrative {
  caveat_codes: CaveatCodes
  fact_ids: FactIds
  text: Text
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Presentation".
 */
export interface Presentation {
  area: Area
  money: Money
  monthly: Monthly2
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "PresentedMonth".
 */
export interface PresentedMonth {
  median_price: Unsigned6 | null
  median_price_per_area: Unsigned6 | null
  month: Month1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Quality".
 */
export interface Quality {
  codes: Codes
  sparse_months: SparseMonths
  status: Status
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "AnalysisRequest".
 */
export interface AnalysisRequest {
  compare_regions: CompareRegions
  criteria: Criteria
  dataset_id: Identifier
  display: Display
  seed: Seed
  window_end: Month1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Criteria".
 */
export interface Criteria {
  bedrooms_max: BedroomsMax
  bedrooms_min: BedroomsMin
  price_max_cents: NonnegativeInt | null
  price_min_cents: NonnegativeInt | null
  property_types: PropertyTypes
  sqft_max: PositiveInt | null
  sqft_min: PositiveInt | null
  zips: Zips
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Display".
 */
export interface Display {
  area: Area1
  money: Money1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Bootstrap".
 */
export interface Bootstrap {
  captures: Captures
  contract_version: ContractVersion1
  dataset: DatasetManifest
  default_request: AnalysisRequest
  fast_agent_version: FastAgentVersion
  live_model_profile: LiveModelProfile
  live_model_requirements: LiveModelRequirements
  mr_catalog: MrCatalog
  python_version: PythonVersion1
  seed_values: SeedValues
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CaptureSummary".
 */
export interface CaptureSummary {
  description: Description
  id: CaptureId
  model_decisions: NonnegativeInt
  purpose: Purpose1
  request: AnalysisRequest
  title: Title
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "DatasetManifest".
 */
export interface DatasetManifest {
  actual_rows: NonnegativeInt
  data_license: DataLicense
  dataset_id: Identifier
  expected_rows: NonnegativeInt
  generated_at_utc: GeneratedAtUtc
  generator: GeneratorProvenance | null
  limitations: Limitations
  logical_multiset_sha256: Sha256
  month_completeness: MonthCompleteness
  month_end: Month1
  month_start: Month1
  partition_row_counts: PartitionRowCounts
  property_types: PropertyTypes1
  quarantined_rows: NonnegativeInt
  row_schema_sha256: Sha256
  schema_version: SchemaVersion
  snapshot_path: SnapshotPath
  snapshot_sha256: Sha256
  source_kind: SourceKind
  unbucketed_rows: NonnegativeInt
  valid_rows: NonnegativeInt
  zips: Zips1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "GeneratorProvenance".
 */
export interface GeneratorProvenance {
  algorithm: Algorithm
  config_path: ConfigPath
  config_sha256: Sha256
  dependency_sha256: DependencySha256
  path: Path
  python_version: PythonVersion
  seed: NonnegativeInt
  sha256: Sha256
}
export interface DependencySha256 {
  [k: string]: Sha256
}
export interface MonthCompleteness {
  [k: string]: 'complete' | 'incomplete'
}
export interface PartitionRowCounts {
  [k: string]: NonnegativeInt
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CatalogEntry".
 */
export interface CatalogEntry {
  compared_fields: ComparedFields
  family: Family
  id: MRId
  preconditions: Preconditions
  relation: Relation
  title: Title1
  tolerances: Tolerances
  witness: Witness
}
export interface Tolerances {
  [k: string]: string
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CaseDetail".
 */
export interface CaseDetail {
  followup: AnalysisView | null
  recipe: Recipe
  result: CaseResult
  source: AnalysisView | null
  witness: Witness1
}
export interface Recipe {
  [k: string]: JsonValue
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CaseResult".
 */
export interface CaseResult {
  base_id: BaseId
  base_semantic_sha256: Sha256
  campaign_id: CampaignId
  cohort_case_sha256: Sha256
  comparison: Comparison | null
  eligibility_path: EligibilityPath
  followup: LegOutcome
  live_campaign_id: LiveCampaignId1
  mode: Mode1
  mr_id: MRId
  mr_version: MrVersion
  reason_codes: ReasonCodes
  schema_version: SchemaVersion1
  seed: Seed1
  slice_group: SliceGroup
  source: LegOutcome
  source_reused_from: SourceReusedFrom
  status: Status4
  transform_sha256: Sha256
  violation_kind: ViolationKind
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Comparison".
 */
export interface Comparison {
  compared_numeric_count: NonnegativeInt
  differences: Differences
  max_absolute_error: MaxAbsoluteError
  status: Status2
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Difference".
 */
export interface Difference {
  absolute_error?: AbsoluteError
  expected: JsonValue
  followup: JsonValue
  path: Path1
  rule: Rule
  source: JsonValue
  tolerance?: Tolerance
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "LegOutcome".
 */
export interface LegOutcome {
  canonical_sha256: Sha256 | null
  capture_path: CapturePath
  duration_ns: NonnegativeInt
  effective_seed: EffectiveSeed
  error_code: ErrorCode | null
  error_stage: ErrorStage
  execution_key: Sha256
  output_sha256: Sha256 | null
  request_sha256: Sha256
  requested_seed: RequestedSeed
  run_id: RunId
  run_path: RunPath
  status: Status3
  view_sha256: Sha256
}
export interface Witness1 {
  [k: string]: JsonValue
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CaseIndexItem".
 */
export interface CaseIndexItem {
  base_id: BaseId1
  key: Key
  mr_id: MrId
  seed: Seed2
  source_reused: SourceReused
  status: Status5
  violation_kind: ViolationKind1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "ErrorInfo".
 */
export interface ErrorInfo {
  code: Code
  message: Message
  stage: Stage
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "ExperimentView".
 */
export interface ExperimentView {
  campaigns: Campaigns
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "CampaignOverview".
 */
export interface CampaignOverview {
  cohort_path: CohortPath
  completed_comparisons: NonnegativeInt
  expected_comparisons: NonnegativeInt
  headlines: Headlines
  id: Id
  last_case: LastCase
  last_status: LastStatus
  mode: Mode3
  scope: Scope
  seeds: Seeds
  state: State
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "HeadlineDisplay".
 */
export interface HeadlineDisplay {
  base_rate: BaseRate
  base_rate_label: BaseRateLabel
  campaign_id: CampaignId1
  ci95_high: Ci95High
  ci95_label: Ci95Label
  ci95_low: Ci95Low
  ci_method: CiMethod
  ci_unit: CiUnit
  complete: Complete
  completed_bases: NonnegativeInt
  eligible_bases: NonnegativeInt
  execution_errors: NonnegativeInt
  family: Family1
  interpretation: Interpretation
  invalid_candidates: NonnegativeInt
  live_campaign_id: LiveCampaignId2
  mode: Mode2
  mr_id: MRId
  output_contract_violations: NonnegativeInt
  schema_version: SchemaVersion2
  seed_pair_violations: NonnegativeInt
  seed_pairs_completed: NonnegativeInt
  seed_values: SeedValues1
  violating_bases: NonnegativeInt
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Job".
 */
export interface Job {
  created_at_utc: CreatedAtUtc
  error: ErrorInfo | null
  id: Id1
  output: AnalysisOutput | null
  state: State1
  submission: Submission
  updated_at_utc: UpdatedAtUtc
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "Submission".
 */
export interface Submission {
  capture_id?: CaptureId | null
  mode: Mode4
  request: AnalysisRequest
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "ModelTurn".
 */
export interface ModelTurn {
  budget: Budget
  dispatched: Dispatched
  input: Input
  response: Response
  sequence: NonnegativeInt
}
export interface Budget {
  [k: string]: JsonValue
}
export interface Input {
  [k: string]: JsonValue
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "WorkflowView".
 */
export interface WorkflowView {
  events: Events
  evidence_scope: EvidenceScope
  failure: ErrorInfo | null
  mode: Mode
  model_decisions: NonnegativeInt
  query_unchanged: QueryUnchanged
  refinements: NonnegativeInt
  run_id: RunId2
  schema_repairs: NonnegativeInt
  status: Status6
  trace_url: TraceUrl1
}
/**
 * This interface was referenced by `ClientContracts`'s JSON-Schema
 * via the `definition` "TraceEvent".
 */
export interface TraceEvent {
  actor: Actor
  dataset_view_sha256: Sha256
  event: Event
  illustrative_fixture: IllustrativeFixture
  iteration: NonnegativeInt
  mode: Mode
  parent_event_sequence: ParentEventSequence
  payload: Payload
  payload_sha256: Sha256
  plan_sha256: Sha256 | null
  query_sha256: Sha256
  run_id: RunId1
  schema_version: SchemaVersion3
  sequence: NonnegativeInt
  timestamp_utc: TimestampUtc
}
export interface Payload {
  [k: string]: JsonValue
}
