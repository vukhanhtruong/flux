import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./Layout";

// Mock the Sidebar to isolate testing
vi.mock("./Sidebar", () => ({
  Sidebar: ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => (
    <div data-testid="sidebar" data-is-open={isOpen}>
      <button onClick={onClose} data-testid="sidebar-close">
        Close Sidebar
      </button>
    </div>
  ),
}));

describe("Layout", () => {
  it("should render header and child outlet", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div data-testid="child">Child Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("flux")).toBeInTheDocument();
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("should toggle sidebar open on menu click", async () => {
    // Suppress console error if any
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-is-open", "false");

    // Click the top menu button
    const menuButtons = document.querySelectorAll("button");
    const topMenuButton = Array.from(menuButtons).find(btn => btn.querySelector("svg"));
    
    if (topMenuButton) {
      fireEvent.click(topMenuButton);
    }
    
    // Check if sidebar receives isOpen = true
    await waitFor(() => {
      expect(sidebar).toHaveAttribute("data-is-open", "true");
    });

    // Sub-test closing
    fireEvent.click(screen.getByTestId("sidebar-close"));
    
    await waitFor(() => {
      expect(sidebar).toHaveAttribute("data-is-open", "false");
    });
  });
});
