import type {
  Transaction,
  TransactionCreate,
  Budget,
  BudgetSet,
  Goal,
  GoalCreate,
  GoalUpdate,
  Subscription,
  SubscriptionCreate,
  Asset,
  AssetCreate,
  SpendingReport,
  FinancialHealth,
  UserProfile,
  UserProfileUpdate,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    // Handle 204 No Content responses
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Transactions
  async listTransactions(userId: string, limit?: number): Promise<Transaction[]> {
    const params = new URLSearchParams({ user_id: userId });
    if (limit) params.append("limit", limit.toString());
    return this.request(`/transactions/?${params}`);
  }

  async getTransaction(id: string, userId: string): Promise<Transaction> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/transactions/${id}?${params}`);
  }

  async createTransaction(data: TransactionCreate): Promise<Transaction> {
    return this.request("/transactions/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteTransaction(id: string, userId: string): Promise<void> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/transactions/${id}?${params}`, {
      method: "DELETE",
    });
  }

  // Budgets
  async listBudgets(userId: string): Promise<Budget[]> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/budgets/?${params}`);
  }

  async setBudget(data: BudgetSet): Promise<Budget> {
    return this.request("/budgets/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteBudget(id: string, userId: string): Promise<void> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/budgets/${id}?${params}`, {
      method: "DELETE",
    });
  }

  // Goals
  async listGoals(userId: string): Promise<Goal[]> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/goals/?${params}`);
  }

  async createGoal(data: GoalCreate): Promise<Goal> {
    return this.request("/goals/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateGoal(id: string, userId: string, data: GoalUpdate): Promise<Goal> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/goals/${id}?${params}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteGoal(id: string, userId: string): Promise<void> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/goals/${id}?${params}`, {
      method: "DELETE",
    });
  }

  // Subscriptions
  async listSubscriptions(userId: string): Promise<Subscription[]> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/subscriptions/?${params}`);
  }

  async createSubscription(data: SubscriptionCreate): Promise<Subscription> {
    return this.request("/subscriptions/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteSubscription(id: string, userId: string): Promise<void> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/subscriptions/${id}?${params}`, {
      method: "DELETE",
    });
  }

  // Assets
  async listAssets(userId: string): Promise<Asset[]> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/assets/?${params}`);
  }

  async createAsset(data: AssetCreate): Promise<Asset> {
    return this.request("/assets/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteAsset(id: string, userId: string): Promise<void> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/assets/${id}?${params}`, {
      method: "DELETE",
    });
  }

  // Analytics
  async getSpendingReport(
    userId: string,
    startDate: string,
    endDate: string
  ): Promise<SpendingReport> {
    const params = new URLSearchParams({
      user_id: userId,
      start_date: startDate,
      end_date: endDate,
    });
    return this.request(`/analytics/spending-report?${params}`);
  }

  async getFinancialHealth(
    userId: string,
    startDate: string,
    endDate: string
  ): Promise<FinancialHealth> {
    const params = new URLSearchParams({
      user_id: userId,
      start_date: startDate,
      end_date: endDate,
    });
    return this.request(`/analytics/financial-health?${params}`);
  }

  // Profile
  async getProfile(userId: string): Promise<UserProfile> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/profile?${params}`);
  }

  async updateProfile(userId: string, data: UserProfileUpdate): Promise<UserProfile> {
    const params = new URLSearchParams({ user_id: userId });
    return this.request(`/profile?${params}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }
}

// Export singleton instance
export const api = new ApiClient();
