import { formatPnl, getPnlClass } from "@/lib/utils";

interface Props {
  pnl: number | null;
  label?: string;
}

export function PnlBadge({ pnl, label }: Props) {
  return (
    <span className={getPnlClass(pnl)} title={label ? `${label}: Tính từ giá mở cửa T+1` : "Tính từ giá mở cửa T+1"}>
      {formatPnl(pnl)}
    </span>
  );
}
