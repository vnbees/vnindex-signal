import { NewsfeedView } from "@/components/NewsfeedView";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: { admin?: string };
}) {
  const isAdmin = searchParams?.admin === "true";
  return <NewsfeedView isAdmin={isAdmin} />;
}
