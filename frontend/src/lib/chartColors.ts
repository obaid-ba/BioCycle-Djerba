import { useTheme } from "@/context/theme";

/**
 * Categorical series colors, validated with the data-viz palette validator
 * (light & dark, both modes ALL CHECKS PASS; worst adjacent CVD ΔE ~70).
 * Organic → aqua (semantically green, brand-aligned); non-organic → blue.
 * Aqua is sub-3:1 on the light surface, so every chart using these ships a
 * legend / direct labels (the relief rule) — identity is never color-alone.
 */
const SERIES = {
  organic: { light: "#1baf7a", dark: "#199e70" },
  nonOrganic: { light: "#2a78d6", dark: "#3987e5" },
} as const;

const GRID = { light: "#e1e0d9", dark: "#2c2c2a" } as const;
const AXIS = { light: "#898781", dark: "#898781" } as const;

export interface ChartColors {
  organic: string;
  nonOrganic: string;
  grid: string;
  axis: string;
}

/** Resolve the validated chart colors for the active theme. */
export function useChartColors(): ChartColors {
  const { theme } = useTheme();
  return {
    organic: SERIES.organic[theme],
    nonOrganic: SERIES.nonOrganic[theme],
    grid: GRID[theme],
    axis: AXIS[theme],
  };
}
