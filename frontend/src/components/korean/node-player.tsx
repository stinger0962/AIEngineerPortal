"use client";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { koreanApi } from "@/lib/korean/api";
import type {
  BossContent,
  DrillContent,
  NodeDetail,
  ReadingContent,
  SceneContent,
} from "@/lib/korean/types";
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

  if (isLoading || !node) return <div className="p-8 opacity-60">Loading…</div>;

  const onDone = (stars: number) => complete.mutate(stars);

  return (
    <div className="mx-auto max-w-2xl p-6">
      <button className="mb-4 text-sm opacity-60 hover:opacity-100" onClick={() => router.push("/korean")}>
        ← Map
      </button>
      <h1 className="mb-4 text-xl font-semibold">{node.title}</h1>
      {node.kind === "reading" && <ReadingNode content={node.content_json as ReadingContent} onDone={onDone} />}
      {node.kind === "scene" && <SceneNode content={node.content_json as SceneContent} onDone={onDone} />}
      {node.kind === "drill" && <DrillNode content={node.content_json as DrillContent} onDone={onDone} />}
      {node.kind === "boss" && <BossNode slug={slug} content={node.content_json as BossContent} onDone={onDone} />}
    </div>
  );
}
