"use client";

import { useState } from "react";

import { portalApi } from "@/lib/api/portal";

export function LessonCompleteButton({ lessonId }: { lessonId: number }) {
  const [status, setStatus] = useState("Mark complete");

  async function onClick() {
    setStatus("Saving...");
    await portalApi.completeLesson(lessonId);
    setStatus("Completed");
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
    >
      {status}
    </button>
  );
}
