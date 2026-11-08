/** Build-time product boundary. Never infer mode from an untrusted Host header. */
export const paidProduct = process.env.NEXT_PUBLIC_PRODUCT_MODE === "paid";
export const productName = paidProduct ? "方寸 · 玄" : "AI Engineer Portal";

export type ProductFeature = {
  id: string;
  href: string;
  label: string;
  english: string;
  character: string;
  description: string;
  accent: string;
};

/** Add a feature here, its page, and the matching API router to extend the product. */
export const paidFeatures: readonly ProductFeature[] = [
  { id: "ziwei", href: "/ziwei", label: "紫微斗数", english: "Ziwei", character: "紫", description: "3D 星盘 · AI 解盘 · 叙事配音", accent: "#9a7bf0" },
  { id: "qian", href: "/qian", label: "灵签求签", english: "Qian", character: "灵", description: "摇签 · 观音灵签 · AI 解签", accent: "#d6a84a" },
];

export function isPaidProductPath(pathname: string): boolean {
  return pathname === "/" || pathname === "/features" || paidFeatures.some(
    ({ href }) => pathname === href || pathname.startsWith(`${href}/`),
  );
}
