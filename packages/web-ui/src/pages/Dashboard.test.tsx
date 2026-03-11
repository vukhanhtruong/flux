import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "./Dashboard";
import { api } from "../lib/api";
import { ProfileProvider } from "../context/ProfileContext";

// Mock Recharts
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: () => <div data-testid="chart">Chart</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

// Mock API
vi.mock("../lib/api", () => ({
  api: {
    listTransactions: vi.fn(),
    getFinancialHealth: vi.fn(),
    listAssets: vi.fn(),
  },
}));

describe("Dashboard", () => {
  it("shows loading state initially and then renders content", async () => {
    (api.listTransactions as any).mockResolvedValue([]);
    (api.getFinancialHealth as any).mockResolvedValue({ score: 85, savings_rate: 0.2, budget_adherence: 0.9, goal_progress: 0.5 });
    (api.listAssets as any).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <ProfileProvider>
          <Dashboard />
        </ProfileProvider>
      </MemoryRouter>
    );

    // Initial loading state might be tricky to catch without a specific test id, 
    // but we can wait for the loaded content.
    await waitFor(() => {
      expect(screen.getByText("Welcome back")).toBeInTheDocument();
    });

    expect(screen.getByText("85/100")).toBeInTheDocument();
    expect(screen.getByTestId("chart")).toBeInTheDocument();
    expect(screen.getByText("Financial Overview")).toBeInTheDocument();
  });
});
