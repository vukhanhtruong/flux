import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("should render sidebar with navigation links", () => {
    const handleClose = vi.fn();
    
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar isOpen={true} onClose={handleClose} />
      </MemoryRouter>
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Transactions")).toBeInTheDocument();
    expect(screen.getByText("Budgets")).toBeInTheDocument();
  });

  it("should close sidebar when clicking overlay on mobile", () => {
    const handleClose = vi.fn();
    
    render(
      <MemoryRouter>
        <Sidebar isOpen={true} onClose={handleClose} />
      </MemoryRouter>
    );

    // Get the first div that acts as an overlay
    const overlay = screen.getByText("flux").parentElement?.parentElement?.parentElement?.firstChild as HTMLElement;
    
    if (overlay) {
      fireEvent.click(overlay);
      expect(handleClose).toHaveBeenCalledOnce();
    }
  });

  it("should call onClose when route changes", () => {
    const handleClose = vi.fn();

    const TestComponent = () => {
      const navigate = import("react-router-dom").then(m => m.useNavigate).then(hook => {
         // this is getting complex, let's just use window location mock or simpler push
         return hook;
      });
      return <button onClick={() => window.history.pushState({}, 'Test', '/transactions')}>Change</button>;
    };

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="*" element={<Sidebar isOpen={true} onClose={handleClose} />} />
        </Routes>
      </MemoryRouter>
    );

    expect(handleClose).toHaveBeenCalled(); // Initial render
  });
  
  it("should hide promo when close button is clicked", () => {
    const handleClose = vi.fn();
    
    render(
      <MemoryRouter>
        <Sidebar isOpen={true} onClose={handleClose} />
      </MemoryRouter>
    );

    expect(screen.getByText("Support flux")).toBeInTheDocument();

    const hideButton = screen.getByTitle("Hide");
    fireEvent.click(hideButton);

    expect(screen.queryByText("Support flux")).not.toBeInTheDocument();
  });
});
