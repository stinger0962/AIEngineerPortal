import { notFound } from "next/navigation";
import { paidProduct } from "@/lib/product/config";
import { PaidAccountPanel } from "@/components/product/account-panel";

export default function AccountPage() {
  if (!paidProduct) notFound();
  return <PaidAccountPanel />;
}
