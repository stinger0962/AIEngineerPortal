"use client";

import { useState } from "react";

import { portalApi } from "@/lib/api/portal";

export function ExerciseAttemptForm({
  exerciseId,
  starterCode,
}: {
  exerciseId: number;
  starterCode: string;
}) {
  const [code, setCode] = useState(starterCode);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("Submit attempt");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Submitting...");
    const attempt = await portalApi.submitAttempt(exerciseId, code, notes);
    setStatus(`Saved (${attempt.score})`);
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <textarea
        value={code}
        onChange={(event) => setCode(event.target.value)}
        className="min-h-64 w-full rounded-3xl border border-ink/10 bg-[#fffdf7] p-4 font-mono text-sm text-ink"
      />
      <textarea
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
        placeholder="Notes about what felt easy, awkward, or worth revisiting..."
        className="min-h-24 w-full rounded-3xl border border-ink/10 bg-white p-4 text-sm text-ink"
      />
      <button type="submit" className="rounded-full bg-pine px-5 py-3 text-sm font-semibold text-white">
        {status}
      </button>
    </form>
  );
}
