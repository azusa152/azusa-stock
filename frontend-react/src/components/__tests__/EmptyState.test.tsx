import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("renders the provided message", () => {
    render(<EmptyState message="No stocks found" />);
    expect(screen.getByText("No stocks found")).toBeInTheDocument();
  });

  it("renders the default icon when no icon is provided", () => {
    render(<EmptyState message="Empty" />);
    expect(screen.getByText("📭")).toBeInTheDocument();
  });

  it("renders a custom icon when provided", () => {
    render(<EmptyState icon="🔍" message="Nothing here" />);
    expect(screen.getByText("🔍")).toBeInTheDocument();
  });

  it("does not render an action button when action prop is omitted", () => {
    render(<EmptyState message="No data" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders and calls the action button when provided", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(
      <EmptyState
        message="No data"
        action={{ label: "Add stock", onClick: handleClick }}
      />
    );
    const button = screen.getByRole("button", { name: "Add stock" });
    expect(button).toBeInTheDocument();
    await user.click(button);
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
