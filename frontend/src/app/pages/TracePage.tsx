import AdvancedPanel from "../../features/advanced/AdvancedPanel";
import { useWeatherWearSession } from "../state/WeatherWearSession";

export default function TracePage() {
  const {
    resultVm,
    runtimeHealth,
    runtimeHealthLoading,
    mapRuntimeDiagnostics,
    activeAdvancedTab,
    setActiveAdvancedTab,
  } = useWeatherWearSession();

  return (
    <AdvancedPanel
      resultVm={resultVm}
      viewMode="developer"
      isOpen
      activeTab={activeAdvancedTab}
      health={runtimeHealth}
      healthLoading={runtimeHealthLoading}
      mapRuntimeDiagnostics={mapRuntimeDiagnostics}
      onToggleOpen={() => undefined}
      onTabChange={setActiveAdvancedTab}
      forceExpanded
    />
  );
}
