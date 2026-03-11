import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

const ProblemChild = () => {
  throw new Error("Test error crash!");
  return null;
};

const SafeChild = () => <div>Safe Content</div>;

describe("ErrorBoundary", () => {
  it("should render children when there is no error", () => {
    render(
      <ErrorBoundary>
        <SafeChild />
      </ErrorBoundary>
    );

    expect(screen.getByText("Safe Content")).toBeInTheDocument();
  });

  it("should catch errors and render fallback UI", () => {
    // Suppress console.error for this expected error test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test error crash!")).toBeInTheDocument();
    
    consoleSpy.mockRestore();
  });
  
  it("should render custom fallback if provided", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<div>Custom Error View</div>}>
        <ProblemChild />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom Error View")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it("should allow resetting the error boundary", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    
    // Mock window.location.reload
    const originalLocation = window.location;
    delete (window as any).location;
    window.location = { ...originalLocation, reload: vi.fn() };

    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>
    );

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(window.location.reload).toHaveBeenCalled();

    // Restore window.location
    window.location = originalLocation;
    consoleSpy.mockRestore();
  });
});
