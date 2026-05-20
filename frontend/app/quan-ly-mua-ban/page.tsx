import type { Metadata } from "next";
import { StockPositionManager } from "@/components/StockPositionManager";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Quản lý mua bán",
  description: "Nhập và theo dõi tín hiệu mua bán cổ phiếu thủ công.",
};

export default function QuanLyMuaBanPage() {
  return <StockPositionManager />;
}
