"use client";

import { useState } from "react";
import { computeChart } from "@/lib/ziwei/chart";
import { TIME_LABELS, RELATION_LABELS } from "@/lib/ziwei/constants";
import { ziweiApi, ZiweiApiError, type ZiweiProfileOut } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";

const inputCls =
  "w-full rounded-xl border border-violet-500/30 bg-[#120a2e] px-3 py-2 text-sm text-violet-100 placeholder:text-violet-300/30 focus:border-violet-400 focus:outline-none";
const labelCls = "block text-xs font-semibold text-violet-300/70 mb-1";

export function ProfileForm({ onCreated, onCancel }: { onCreated: (p: ZiweiProfileOut) => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("self");
  const [gender, setGender] = useState<"male" | "female">("female");
  const [isLunar, setIsLunar] = useState(false);
  const [isLeapMonth, setIsLeapMonth] = useState(false);
  const [birthDate, setBirthDate] = useState("");
  const [timeIndex, setTimeIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) return setError("请填写姓名/称呼");
    if (!/^\d{4}-\d{1,2}-\d{1,2}$/.test(birthDate)) return setError("生日格式应为 YYYY-M-D，例如 1990-8-16");
    setSubmitting(true);

    // 第一段：浏览器内排盘——任何 throw 都是排盘/生辰问题
    let chart: ZiweiChart;
    try {
      chart = computeChart({ dateStr: birthDate, timeIndex, gender, isLunar, isLeapMonth });
    } catch {
      setError("排盘失败，请检查生辰是否正确");
      setSubmitting(false);
      return;
    }

    // 第二段：保存到后端——任何 throw（HTTP 错误或网络断连）都是保存问题
    try {
      const profile = await ziweiApi.createProfile({
        name: name.trim(),
        relation,
        gender,
        birth_date: birthDate,
        birth_time_index: timeIndex,
        is_lunar_input: isLunar,
        is_leap_month: isLeapMonth,
        chart_json: chart,
      });
      onCreated(profile);
    } catch (e) {
      setError(e instanceof ZiweiApiError && e.status === 400 ? `保存被拒绝：${e.message}` : "保存失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 rounded-[28px] border border-violet-500/20 bg-[#0d0722] p-5">
      <h3 className="text-sm font-semibold tracking-[0.2em] text-violet-200">新建命主档案</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>姓名 / 称呼</label>
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="如：妈妈" />
        </div>
        <div>
          <label className={labelCls}>关系</label>
          <select className={inputCls} value={relation} onChange={(e) => setRelation(e.target.value)}>
            {Object.entries(RELATION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>性别</label>
          <select className={inputCls} value={gender} onChange={(e) => setGender(e.target.value as "male" | "female")}>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>历法</label>
          <select
            className={inputCls}
            value={isLunar ? "lunar" : "solar"}
            onChange={(e) => {
              setIsLunar(e.target.value === "lunar");
              if (e.target.value !== "lunar") setIsLeapMonth(false);
            }}
          >
            <option value="solar">公历（阳历）</option>
            <option value="lunar">农历（阴历）</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>出生日期（{isLunar ? "农历" : "公历"} YYYY-M-D）</label>
          <input className={inputCls} value={birthDate} onChange={(e) => setBirthDate(e.target.value)} placeholder="1990-8-16" />
        </div>
        <div>
          <label className={labelCls}>出生时辰</label>
          <select className={inputCls} value={timeIndex} onChange={(e) => setTimeIndex(Number(e.target.value))}>
            {TIME_LABELS.map((label, index) => (
              <option key={label} value={index}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLunar ? (
        <label className="flex items-center gap-2 text-xs text-violet-300/70">
          <input type="checkbox" checked={isLeapMonth} onChange={(e) => setIsLeapMonth(e.target.checked)} />
          出生月为闰月
        </label>
      ) : null}

      {error ? <p className="text-xs text-rose-400">{error}</p> : null}

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 py-2.5 text-sm font-semibold text-white shadow-[0_4px_14px_rgba(139,92,246,0.4)] transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "排盘中……" : "排盘建档"}
        </button>
        <button onClick={onCancel} className="rounded-xl border border-violet-500/30 px-4 py-2.5 text-sm text-violet-300">
          取消
        </button>
      </div>
    </div>
  );
}
