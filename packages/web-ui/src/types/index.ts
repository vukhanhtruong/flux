// Transaction types
export type TransactionType = "income" | "expense";

export interface Transaction {
  id: string;
  user_id: string;
  date: string;
  amount: string;
  category: string;
  description: string;
  type: TransactionType;
  is_recurring: boolean;
  tags: string[];
  created_at: string;
}

export interface TransactionCreate {
  user_id: string;
  date: string;
  amount: number;
  category: string;
  description: string;
  type: TransactionType;
  is_recurring?: boolean;
  tags?: string[];
}

// Budget types
export interface Budget {
  id: string;
  user_id: string;
  category: string;
  monthly_limit: string;
  created_at: string;
}

export interface BudgetSet {
  user_id: string;
  category: string;
  monthly_limit: number;
}

// Goal types
export interface Goal {
  id: string;
  user_id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  deadline: string;
  created_at: string;
}

export interface GoalCreate {
  user_id: string;
  name: string;
  target_amount: number;
  current_amount?: number;
  deadline: string;
}

export interface GoalUpdate {
  current_amount?: number;
  deadline?: string;
}

// Subscription types
export interface Subscription {
  id: string;
  user_id: string;
  name: string;
  amount: string;
  billing_cycle: string;
  next_date: string;
  category: string;
  active: boolean;
}

export interface SubscriptionCreate {
  user_id: string;
  name: string;
  amount: number;
  billing_cycle: string;
  next_date: string;
  category: string;
}

// Asset types
export interface Asset {
  id: string;
  user_id: string;
  name: string;
  value?: string;
  amount?: string;
  interest_rate?: string;
  frequency?: string;
  next_date?: string;
  category?: string;
  active?: boolean;
  asset_type: string;
  created_at?: string;
}

export interface AssetCreate {
  user_id: string;
  name: string;
  value: number;
  asset_type: string;
}

// Analytics types
export interface SpendingReport {
  total_income: string;
  total_expenses: string;
  net: string;
  count: number;
  category_breakdown: { category: string; total: string; count: number }[];
  start_date: string;
  end_date: string;
}

export interface FinancialHealth {
  score: number;
  savings_rate: number;
  budget_adherence: number;
  goal_progress: number;
}

// User profile types
export interface UserProfile {
  user_id: string;
  username: string;
  channel: string;
  platform_id: string;
  currency: string;
  timezone: string;
  locale: string;
}

export interface UserProfileUpdate {
  currency?: string;
  timezone?: string;
  locale?: string;
}

// Backup types
export interface BackupMetadata {
  id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
  storage: "local" | "s3";
  s3_key?: string;
  local_path?: string;
}

export interface S3Config {
  s3_endpoint: string;
  s3_bucket: string;
  s3_region: string;
  s3_access_key: string;
  s3_secret_key: string;
}

// Scheduled task types
export interface ScheduledTask {
  id: number;
  user_id: string;
  prompt: string;
  schedule_type: "once" | "cron" | "interval";
  schedule_value: string;
  status: "active" | "paused" | "completed";
  next_run_at: string;
  last_run_at: string | null;
  subscription_id: string | null;
  asset_id: string | null;
  created_at: string;
}
