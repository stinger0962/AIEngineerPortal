import { NodePlayer } from "@/components/korean/node-player";

export default async function KoreanNodePage({
  params,
}: {
  params: Promise<{ nodeSlug: string }>;
}) {
  const { nodeSlug } = await params;
  return <NodePlayer slug={nodeSlug} />;
}
