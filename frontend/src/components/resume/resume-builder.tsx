"use client";

import { useState } from "react";
import { portalApi } from "@/lib/api/portal";
import type { ResumeInput, ResumeOutput } from "@/lib/types/portal";
import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { Check, Copy, Download, Plus, RefreshCw, Trash2 } from "lucide-react";

// ─── types ────────────────────────────────────────────────────────────────────

interface WorkEntry {
  company: string;
  role: string;
  dates: string;
  bullets: string; // raw textarea – one bullet per line
}

interface EduEntry {
  school: string;
  degree: string;
  year: string;
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function emptyWork(): WorkEntry {
  return { company: "", role: "", dates: "", bullets: "" };
}

function emptyEdu(): EduEntry {
  return { school: "", degree: "", year: "" };
}

function inputCls(extra = "") {
  return `w-full rounded-xl border border-ink/20 bg-cream/60 px-4 py-2.5 text-sm text-ink placeholder:text-ink/40 outline-none transition focus:border-ember focus:ring-2 focus:ring-ember/20 ${extra}`;
}

function labelCls() {
  return "block text-xs font-semibold uppercase tracking-[0.2em] text-ink/60 mb-1.5";
}

// ─── step indicator ───────────────────────────────────────────────────────────

function StepBar({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 mb-6">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-1.5 flex-1 rounded-full transition-all ${
            i < current ? "bg-ember" : i === current ? "bg-ember/50" : "bg-ink/10"
          }`}
        />
      ))}
      <span className="ml-2 text-xs font-medium text-ink/50 whitespace-nowrap">
        {current + 1} / {total}
      </span>
    </div>
  );
}

// ─── nav buttons ──────────────────────────────────────────────────────────────

function NavButtons({
  step,
  totalSteps,
  onPrev,
  onNext,
  onGenerate,
  loading,
}: {
  step: number;
  totalSteps: number;
  onPrev: () => void;
  onNext: () => void;
  onGenerate: () => void;
  loading: boolean;
}) {
  const isLast = step === totalSteps - 1;
  return (
    <div className="flex justify-between mt-8 pt-6 border-t border-ink/10">
      <button
        onClick={onPrev}
        disabled={step === 0}
        className="rounded-xl border border-ink/20 px-5 py-2.5 text-sm font-medium text-ink/70 transition hover:bg-ink/5 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Previous
      </button>
      {isLast ? (
        <button
          onClick={onGenerate}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl bg-ember px-6 py-2.5 text-sm font-semibold text-cream shadow-sm transition hover:bg-ember/90 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <RefreshCw size={15} className="animate-spin" />
              Generating…
            </>
          ) : (
            "Generate Resume"
          )}
        </button>
      ) : (
        <button
          onClick={onNext}
          className="rounded-xl bg-ink px-6 py-2.5 text-sm font-semibold text-cream transition hover:bg-ink/80"
        >
          Next
        </button>
      )}
    </div>
  );
}

// ─── step 1: basic info ───────────────────────────────────────────────────────

function Step1({
  data,
  onChange,
}: {
  data: { full_name: string; target_role: string; years_experience: number; current_role: string; summary_override: string };
  onChange: (key: string, value: string | number) => void;
}) {
  return (
    <div className="space-y-5">
      <h2 className="font-display text-xl text-ink">Basic Information</h2>

      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label className={labelCls()}>Full Name</label>
          <input
            className={inputCls()}
            placeholder="Jane Smith"
            value={data.full_name}
            onChange={(e) => onChange("full_name", e.target.value)}
          />
        </div>
        <div>
          <label className={labelCls()}>Target Role</label>
          <input
            className={inputCls()}
            placeholder="AI Engineer"
            value={data.target_role}
            onChange={(e) => onChange("target_role", e.target.value)}
          />
        </div>
        <div>
          <label className={labelCls()}>Current Role</label>
          <input
            className={inputCls()}
            placeholder="Senior Software Engineer"
            value={data.current_role}
            onChange={(e) => onChange("current_role", e.target.value)}
          />
        </div>
        <div>
          <label className={labelCls()}>Years of Experience</label>
          <input
            type="number"
            min={0}
            max={40}
            className={inputCls()}
            value={data.years_experience}
            onChange={(e) => onChange("years_experience", Number(e.target.value))}
          />
        </div>
      </div>

      <div>
        <label className={labelCls()}>Summary Override (optional)</label>
        <textarea
          rows={3}
          className={inputCls("resize-none")}
          placeholder="Leave blank to let Claude generate a tailored summary…"
          value={data.summary_override}
          onChange={(e) => onChange("summary_override", e.target.value)}
        />
      </div>
    </div>
  );
}

// ─── step 2: work experience ─────────────────────────────────────────────────

function Step2({
  entries,
  onChange,
  onAdd,
  onRemove,
}: {
  entries: WorkEntry[];
  onChange: (idx: number, key: keyof WorkEntry, value: string) => void;
  onAdd: () => void;
  onRemove: (idx: number) => void;
}) {
  return (
    <div className="space-y-6">
      <h2 className="font-display text-xl text-ink">Work Experience</h2>
      {entries.map((entry, idx) => (
        <div key={idx} className="relative rounded-2xl border border-ink/10 bg-sand/30 p-5 space-y-4">
          {entries.length > 1 && (
            <button
              onClick={() => onRemove(idx)}
              className="absolute top-4 right-4 text-ink/30 hover:text-red-500 transition"
            >
              <Trash2 size={15} />
            </button>
          )}
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ember">Position {idx + 1}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls()}>Company</label>
              <input
                className={inputCls()}
                placeholder="Acme Corp"
                value={entry.company}
                onChange={(e) => onChange(idx, "company", e.target.value)}
              />
            </div>
            <div>
              <label className={labelCls()}>Role</label>
              <input
                className={inputCls()}
                placeholder="Senior Engineer"
                value={entry.role}
                onChange={(e) => onChange(idx, "role", e.target.value)}
              />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls()}>Dates</label>
              <input
                className={inputCls()}
                placeholder="Jan 2022 – Present"
                value={entry.dates}
                onChange={(e) => onChange(idx, "dates", e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className={labelCls()}>Bullet Points (one per line)</label>
            <textarea
              rows={4}
              className={inputCls("resize-none font-mono text-xs")}
              placeholder={"Built a real-time pipeline processing 1M events/day\nReduced latency by 40% using caching layer"}
              value={entry.bullets}
              onChange={(e) => onChange(idx, "bullets", e.target.value)}
            />
          </div>
        </div>
      ))}
      <button
        onClick={onAdd}
        className="flex items-center gap-2 rounded-xl border border-dashed border-ember/40 px-4 py-3 text-sm text-ember hover:bg-ember/5 transition w-full justify-center"
      >
        <Plus size={15} /> Add Another Position
      </button>
    </div>
  );
}

// ─── step 3: education + skills ──────────────────────────────────────────────

function Step3({
  eduEntries,
  skillsRaw,
  onEduChange,
  onEduAdd,
  onEduRemove,
  onSkillsChange,
}: {
  eduEntries: EduEntry[];
  skillsRaw: string;
  onEduChange: (idx: number, key: keyof EduEntry, value: string) => void;
  onEduAdd: () => void;
  onEduRemove: (idx: number) => void;
  onSkillsChange: (value: string) => void;
}) {
  return (
    <div className="space-y-6">
      <h2 className="font-display text-xl text-ink">Education & Skills</h2>

      <div className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/60">Education</p>
        {eduEntries.map((entry, idx) => (
          <div key={idx} className="relative rounded-2xl border border-ink/10 bg-sand/30 p-5">
            {eduEntries.length > 1 && (
              <button
                onClick={() => onEduRemove(idx)}
                className="absolute top-4 right-4 text-ink/30 hover:text-red-500 transition"
              >
                <Trash2 size={15} />
              </button>
            )}
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label className={labelCls()}>School</label>
                <input
                  className={inputCls()}
                  placeholder="University of Michigan"
                  value={entry.school}
                  onChange={(e) => onEduChange(idx, "school", e.target.value)}
                />
              </div>
              <div>
                <label className={labelCls()}>Year</label>
                <input
                  className={inputCls()}
                  placeholder="2016"
                  value={entry.year}
                  onChange={(e) => onEduChange(idx, "year", e.target.value)}
                />
              </div>
              <div className="sm:col-span-3">
                <label className={labelCls()}>Degree</label>
                <input
                  className={inputCls()}
                  placeholder="B.S. Computer Science"
                  value={entry.degree}
                  onChange={(e) => onEduChange(idx, "degree", e.target.value)}
                />
              </div>
            </div>
          </div>
        ))}
        <button
          onClick={onEduAdd}
          className="flex items-center gap-2 rounded-xl border border-dashed border-ember/40 px-4 py-3 text-sm text-ember hover:bg-ember/5 transition w-full justify-center"
        >
          <Plus size={15} /> Add Another Degree
        </button>
      </div>

      <div>
        <label className={labelCls()}>Skills (comma-separated)</label>
        <textarea
          rows={3}
          className={inputCls("resize-none")}
          placeholder="Python, LangChain, OpenAI API, FastAPI, Docker, PostgreSQL, React…"
          value={skillsRaw}
          onChange={(e) => onSkillsChange(e.target.value)}
        />
        <p className="mt-1.5 text-xs text-ink/40">Claude will enrich this list with skills from your portal activity.</p>
      </div>
    </div>
  );
}

// ─── step 4: review + generate ───────────────────────────────────────────────

function Step4({
  includePortalData,
  onToggle,
  summary,
}: {
  includePortalData: boolean;
  onToggle: () => void;
  summary: {
    name: string;
    role: string;
    years: number;
    workCount: number;
    eduCount: number;
    skillCount: number;
  };
}) {
  return (
    <div className="space-y-6">
      <h2 className="font-display text-xl text-ink">Review & Generate</h2>

      <div className="rounded-2xl border border-ink/10 bg-sand/30 p-5 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/60">Summary</p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-ink/50">Name:</span>{" "}
            <span className="font-medium text-ink">{summary.name || "—"}</span>
          </div>
          <div>
            <span className="text-ink/50">Target Role:</span>{" "}
            <span className="font-medium text-ink">{summary.role || "—"}</span>
          </div>
          <div>
            <span className="text-ink/50">Experience:</span>{" "}
            <span className="font-medium text-ink">{summary.years} years</span>
          </div>
          <div>
            <span className="text-ink/50">Positions:</span>{" "}
            <span className="font-medium text-ink">{summary.workCount}</span>
          </div>
          <div>
            <span className="text-ink/50">Education:</span>{" "}
            <span className="font-medium text-ink">{summary.eduCount} entries</span>
          </div>
          <div>
            <span className="text-ink/50">Skills listed:</span>{" "}
            <span className="font-medium text-ink">{summary.skillCount}</span>
          </div>
        </div>
      </div>

      <button
        onClick={onToggle}
        className={`flex items-center gap-3 w-full rounded-2xl border-2 p-4 transition text-left ${
          includePortalData
            ? "border-ember/60 bg-ember/5"
            : "border-ink/15 bg-transparent hover:border-ink/25"
        }`}
      >
        <div
          className={`flex-shrink-0 w-5 h-5 rounded-md border-2 flex items-center justify-center transition ${
            includePortalData ? "border-ember bg-ember" : "border-ink/30"
          }`}
        >
          {includePortalData && <Check size={12} className="text-cream" strokeWidth={3} />}
        </div>
        <div>
          <p className="text-sm font-semibold text-ink">Include Portal Learning Data</p>
          <p className="text-xs text-ink/50 mt-0.5">
            Claude will pull your completed lessons, exercises, and projects to enrich the resume.
          </p>
        </div>
      </button>

      <div className="rounded-2xl border border-mint/30 bg-mint/10 p-4 text-sm text-pine space-y-1">
        <p className="font-semibold">What Claude will do</p>
        <ul className="list-disc list-inside space-y-0.5 text-pine/80">
          <li>Write a tailored professional summary</li>
          <li>Strengthen your bullet points with impact language</li>
          <li>Curate a skills section from your input + portal data</li>
          <li>Surface AI engineering projects and highlights</li>
          <li>Output a clean Markdown resume you can copy or download</li>
        </ul>
      </div>
    </div>
  );
}

// ─── step 5: result ───────────────────────────────────────────────────────────

function Step5({
  result,
  onRegenerate,
  loading,
}: {
  result: ResumeOutput;
  onRegenerate: () => void;
  loading: boolean;
}) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(result.resume_md).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleDownload() {
    const blob = new Blob([result.resume_md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "resume.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      {/* toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl text-ink">Your Resume</h2>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-xl border border-ink/20 px-3.5 py-2 text-xs font-medium text-ink/70 transition hover:bg-ink/5"
          >
            {copied ? <Check size={13} className="text-pine" /> : <Copy size={13} />}
            {copied ? "Copied!" : "Copy Markdown"}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 rounded-xl border border-ink/20 px-3.5 py-2 text-xs font-medium text-ink/70 transition hover:bg-ink/5"
          >
            <Download size={13} /> Download .md
          </button>
          <button
            onClick={onRegenerate}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl bg-ink px-3.5 py-2 text-xs font-semibold text-cream transition hover:bg-ink/80 disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Regenerate
          </button>
        </div>
      </div>

      {/* AI highlights */}
      {result.ai_engineering_highlights.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pine/70">AI Engineering Highlights</p>
          <div className="flex flex-wrap gap-2">
            {result.ai_engineering_highlights.map((h) => (
              <span
                key={h}
                className="rounded-full bg-mint/20 border border-mint/40 px-3 py-1 text-xs font-medium text-pine"
              >
                {h}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* skills */}
      {result.skills.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/50">Skills</p>
          <div className="flex flex-wrap gap-2">
            {result.skills.map((s) => (
              <span
                key={s}
                className="rounded-full bg-sand border border-ink/10 px-3 py-1 text-xs text-ink/80"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* divider */}
      <div className="border-t border-ink/10" />

      {/* rendered markdown */}
      <div className="prose prose-sm max-w-none">
        <LessonMarkdown content={result.resume_md} />
      </div>

      {/* token info */}
      {(result.model || result.input_tokens) && (
        <p className="text-xs text-ink/30 text-right">
          {result.model && <span>{result.model} · </span>}
          {result.input_tokens && <span>{result.input_tokens.toLocaleString()} in · </span>}
          {result.output_tokens && <span>{result.output_tokens.toLocaleString()} out</span>}
        </p>
      )}
    </div>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

const TOTAL_STEPS = 5; // 0-indexed: 0 basic, 1 work, 2 edu+skills, 3 review, 4 result

export function ResumeBuilder() {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeOutput | null>(null);

  // basic info
  const [basic, setBasic] = useState({
    full_name: "",
    target_role: "AI Engineer",
    years_experience: 5,
    current_role: "",
    summary_override: "",
  });

  // work experience
  const [workEntries, setWorkEntries] = useState<WorkEntry[]>([emptyWork()]);

  // education
  const [eduEntries, setEduEntries] = useState<EduEntry[]>([emptyEdu()]);

  // skills
  const [skillsRaw, setSkillsRaw] = useState("");

  // portal data toggle
  const [includePortalData, setIncludePortalData] = useState(true);

  // ── handlers ──────────────────────────────────────────────────────────────

  function handleBasicChange(key: string, value: string | number) {
    setBasic((prev) => ({ ...prev, [key]: value }));
  }

  function handleWorkChange(idx: number, key: keyof WorkEntry, value: string) {
    setWorkEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, [key]: value } : e)));
  }

  function handleEduChange(idx: number, key: keyof EduEntry, value: string) {
    setEduEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, [key]: value } : e)));
  }

  function buildInput(): ResumeInput {
    return {
      full_name: basic.full_name,
      target_role: basic.target_role,
      years_experience: basic.years_experience,
      current_role: basic.current_role,
      summary_override: basic.summary_override || undefined,
      work_experience: workEntries.map((w) => ({
        company: w.company,
        role: w.role,
        dates: w.dates,
        bullets: w.bullets.split("\n").map((b) => b.trim()).filter(Boolean),
      })),
      education: eduEntries.map((e) => ({ school: e.school, degree: e.degree, year: e.year })),
      projects_override: [],
      skills_override: skillsRaw.split(",").map((s) => s.trim()).filter(Boolean),
      include_portal_data: includePortalData,
    };
  }

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const input = buildInput();
      const output = await portalApi.generateResume(input);
      setResult(output);
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume generation failed");
    } finally {
      setLoading(false);
    }
  }

  function handleRegenerate() {
    setStep(3);
    setResult(null);
  }

  // ── render ────────────────────────────────────────────────────────────────

  // result step (step 4) has no nav bar
  if (step === 4 && result) {
    return (
      <div>
        <StepBar current={4} total={TOTAL_STEPS} />
        <Step5 result={result} onRegenerate={handleRegenerate} loading={loading} />
      </div>
    );
  }

  const formStepCount = 4; // steps 0-3

  return (
    <div>
      <StepBar current={step} total={TOTAL_STEPS} />

      {error && (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {step === 0 && <Step1 data={basic} onChange={handleBasicChange} />}
      {step === 1 && (
        <Step2
          entries={workEntries}
          onChange={handleWorkChange}
          onAdd={() => setWorkEntries((prev) => [...prev, emptyWork()])}
          onRemove={(idx) => setWorkEntries((prev) => prev.filter((_, i) => i !== idx))}
        />
      )}
      {step === 2 && (
        <Step3
          eduEntries={eduEntries}
          skillsRaw={skillsRaw}
          onEduChange={handleEduChange}
          onEduAdd={() => setEduEntries((prev) => [...prev, emptyEdu()])}
          onEduRemove={(idx) => setEduEntries((prev) => prev.filter((_, i) => i !== idx))}
          onSkillsChange={setSkillsRaw}
        />
      )}
      {step === 3 && (
        <Step4
          includePortalData={includePortalData}
          onToggle={() => setIncludePortalData((v) => !v)}
          summary={{
            name: basic.full_name,
            role: basic.target_role,
            years: basic.years_experience,
            workCount: workEntries.filter((w) => w.company).length,
            eduCount: eduEntries.filter((e) => e.school).length,
            skillCount: skillsRaw.split(",").map((s) => s.trim()).filter(Boolean).length,
          }}
        />
      )}

      <NavButtons
        step={step}
        totalSteps={formStepCount}
        onPrev={() => setStep((s) => Math.max(0, s - 1))}
        onNext={() => setStep((s) => Math.min(formStepCount - 1, s + 1))}
        onGenerate={handleGenerate}
        loading={loading}
      />
    </div>
  );
}
