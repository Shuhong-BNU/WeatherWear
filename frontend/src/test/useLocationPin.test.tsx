import { renderHook } from "@testing-library/react";
import { useLocationPin } from "../shared/hooks/useLocationPin";
import { createResultViewModel } from "./mockViewModel";

describe("useLocationPin", () => {
  it("uses the confirmed location pin for map centering after text query", () => {
    const viewModel = createResultViewModel();
    const { result } = renderHook(() => useLocationPin(viewModel.location_pin, null));

    expect(result.current.hasMarker).toBe(true);
    expect(result.current.confirmed).toBe(true);
    expect(result.current.center).toEqual([36.0671, 120.3826]);
    expect(result.current.zoom).toBe(8);
  });
});
