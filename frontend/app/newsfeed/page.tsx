import type { Metadata } from "next";
import { NewsfeedView } from "@/components/NewsfeedView";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Newsfeed tín hiệu mua",
  description: "Danh sách mã cổ phiếu được khuyến nghị mua theo từng ngày phân tích.",
};

export default async function NewsfeedPage({
  searchParams,
}: {
  searchParams: { admin?: string };
}) {
  const isAdmin = searchParams?.admin === "true";
  return <NewsfeedView isAdmin={isAdmin} />;
}
