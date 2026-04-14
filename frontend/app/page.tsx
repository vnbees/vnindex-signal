import { NewsfeedView } from "@/components/NewsfeedView";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  return <NewsfeedView />;
}
