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
  value: string;
  asset_type: string;
  created_at: string;
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
  net_savings: string;
  category_breakdown: Record<string, string>;
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
