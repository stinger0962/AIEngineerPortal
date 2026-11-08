import { paidProduct } from "@/lib/product/config";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? (paidProduct ? "/api/v1" : "http://localhost:8000/api/v1");
