"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { koreanApi } from "@/lib/korean/api";
import type {
  BossContent,
  DrillContent,
  NodeDetail,
  ReadingContent,
  SceneContent,
} from "@/lib/korean/types";
import { KIND_THEME } from "@/lib/korean/theme";
import { KindSeal } from "./ui";
import { Mascot } from "./mascot";
import { ReadingNode } from "./reading-node";
import { SceneNode } from "./scene-node";
import { DrillNode } from "./drill-node";
import { BossNode } from "./boss-node";

export function NodePlayer({ slug }: { slug: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: node, isLoading } = useQuery<NodeDetail>({
    queryKey: ["korean-node", slug],
    queryFn: () => koreanApi.getNode(slug),
  });
  const complete = useMutation({
    mutationFn: (stars: number) => koreanApi.completeNode(slug, 1.0, stars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["korean-map"] });
      router.push("/korean");
    },
  });

  const onDone = (stars: number) => complete.mutate(stars);

  return (
    <div className="k-hanji k-pattern min-h-screen">
      <div className="relative mx-auto max-w-2xl px-5 py-9 sm:px-8">
        <button
          className="k-press font-kr mb-6 inline-flex items-center gap-1.5 rounded-full border border-ink/12 bg-white/55 px-3 py-1.5 text-xs text-ink/55 hover:text-ink"
          onClick={() => router.push("/korean")}
        >
          <span aria-hidden>←</span> 지도 · Map
        </button>

        {isLoading || !node ? (
          <p className="font-kr text-sm text-ink/40">불러오는 중…</p>
        ) : (
          <>
            <header className="k-bounce-in mb-7 flex items-center gap-4">
              <KindSeal kind={node.kind} size={52} />
              <div className="flex-1">
                <p
                  className="text-[11px] font-semibold uppercase tracking-[0.22em]"
                  style={{ color: KIND_THEME[node.kind].accent }}
                >
                  {KIND_THEME[node.kind].label}
                </p>
                <h1 className="font-kr-serif text-2xl text-ink sm:text-3xl">{node.title}</h1>
              </div>
              <Mascot size={56} className="hidden shrink-0 sm:block" />
            </header>

            <div className="k-rise" style={{ animationDelay: "80ms" }}>
              {node.kind === "reading" && <ReadingNode content={node.content_json as ReadingContent} onDone={onDone} />}
              {node.kind === "scene" && <SceneNode content={node.content_json as SceneContent} onDone={onDone} />}
              {node.kind === "drill" && <DrillNode content={node.content_json as DrillContent} onDone={onDone} />}
              {node.kind === "boss" && <BossNode slug={slug} content={node.content_json as BossContent} onDone={onDone} />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
