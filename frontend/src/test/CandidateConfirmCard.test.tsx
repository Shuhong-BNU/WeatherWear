import { render, screen } from "@testing-library/react";
import CandidateConfirmCard from "../features/candidates/CandidateConfirmCard";
import { createResultViewModel } from "./mockViewModel";

describe("CandidateConfirmCard", () => {
  it("renders nothing after the location is already resolved", () => {
    const viewModel = createResultViewModel();

    const { container } = render(
      <CandidateConfirmCard
        resultVm={viewModel}
        selectedCandidateId=""
        showAllCandidates={false}
        isPending={false}
        onSelect={() => undefined}
        onConfirm={() => undefined}
        onToggleShowAll={() => undefined}
        onReselect={() => undefined}
      />,
    );

    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByRole("button", { name: /confirm this place|确认这个地点/i })).not.toBeInTheDocument();
  });
});
