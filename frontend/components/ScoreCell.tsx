interface Props {
  score: number;
}

export function ScoreCell({ score }: Props) {
  let color = "text-slate-500";
  if (score > 0) color = "text-green-600 font-medium";
  else if (score < 0) color = "text-red-600 font-medium";
  return (
    <span className={color}>
      {score > 0 ? `+${score}` : score}
    </span>
  );
}
