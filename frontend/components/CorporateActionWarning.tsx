interface Props {
  show: boolean;
  symbol?: string;
}

export function CorporateActionWarning({ show, symbol }: Props) {
  if (!show) return null;
  return (
    <span
      title={`${symbol ?? ""} - Có thể có split/dividend — cần review thủ công`}
      className="text-amber-400 cursor-help"
    >
      ⚠️
    </span>
  );
}
