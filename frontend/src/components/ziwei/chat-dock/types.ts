import type { CameraCommand, OracleSegment } from "@/lib/ziwei/api";

export type DockState = "collapsed" | "normal" | "expanded";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  segments?: OracleSegment[];
  cameras?: CameraCommand[];
  pending?: boolean; // 回放中（Task 5 用）
};
