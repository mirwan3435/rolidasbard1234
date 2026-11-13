import { create } from "zustand";
import { persist } from "zustand/middleware";

type Pos = { x: number; y: number };

type UiState = {
  symbol: string;
  positions: Record<string, Pos>;
  setSymbol: (symbol: string) => void;
  setPositions: (positions: Record<string, Pos>) => void;
};

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      symbol: "",
      positions: {},
      setSymbol: (symbol) => set({ symbol }),
      setPositions: (positions) => set({ positions }),
    }),
    { name: "dashboard-ui-layout" },
  ),
);
