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

  it("renders title when provided", () => {
    render(<EmptyState message="fallback" title="Get Started" />);
    expect(screen.getByText("Get Started")).toBeInTheDocument();
  });

  it("renders description instead of message when both provided", () => {
    render(
      <EmptyState message="fallback" description="Add stocks to begin" />
    );
    expect(screen.getByText("Add stocks to begin")).toBeInTheDocument();
    expect(screen.queryByText("fallback")).not.toBeInTheDocument();
  });

  it("renders primary and secondary action buttons", async () => {
    const user = userEvent.setup();
    const primaryClick = vi.fn();
    const secondaryClick = vi.fn();
    render(
      <EmptyState
        message="No data"
        action={{ label: "Go to Radar", onClick: primaryClick }}
        secondaryAction={{
          label: "Add Holdings",
          onClick: secondaryClick,
          variant: "outline",
        }}
      />
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Go to Radar" }));
    expect(primaryClick).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Add Holdings" }));
    expect(secondaryClick).toHaveBeenCalledOnce();
  });
});
