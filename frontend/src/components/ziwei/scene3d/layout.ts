/** 3D 方盘布局：沿用 2D 的地支固定位（chart-grid-2d.tsx BRANCH_GRID），映射到 XZ 平面 */

export const CELL_W = 2.6;
export const CELL_D = 3.4;
export const PLATE_H = 0.18;

export const BRANCH_GRID: Record<string, { row: number; col: number }> = {
  巳: { row: 1, col: 1 },
  午: { row: 1, col: 2 },
  未: { row: 1, col: 3 },
  申: { row: 1, col: 4 },
  辰: { row: 2, col: 1 },
  酉: { row: 2, col: 4 },
  卯: { row: 3, col: 1 },
  戌: { row: 3, col: 4 },
  寅: { row: 4, col: 1 },
  丑: { row: 4, col: 2 },
  子: { row: 4, col: 3 },
  亥: { row: 4, col: 4 },
};

export function branchPosition(branch: string): [number, number, number] | null {
  const pos = BRANCH_GRID[branch];
  if (!pos) return null;
  return [(pos.col - 2.5) * CELL_W, 0, (pos.row - 2.5) * CELL_D];
}

/** 四化配色（与 2D MUTAGEN_STYLES 同义，给 three 用的 hex） */
export const MUTAGEN_COLORS: Record<string, string> = {
  禄: "#10b981",
  权: "#d97706",
  科: "#0284c7",
  忌: "#e11d48",
};

export const SOUL_EDGE = "#fbbf24";
export const PLATE_EDGE = "#8b5cf6";
