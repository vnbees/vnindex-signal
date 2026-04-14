import type { Metadata } from "next";
import { NewsfeedView } from "@/components/NewsfeedView";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Newsfeed tín hiệu mua",
  description: "Hiển thị newsfeed tín hiệu mua mới nhất.",
};

export default async function ThongKeTinHieuPage() {
  return <NewsfeedView />;
}
