import { getRecommendationConfig } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Props {
  recommendation: string;
  size?: "sm" | "md";
}

export function RecommendationBadge({ recommendation, size = "sm" }: Props) {
  const config = getRecommendationConfig(recommendation);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium",
        config.color,
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"
      )}
    >
      {config.emoji} {config.label}
    </span>
  );
}
