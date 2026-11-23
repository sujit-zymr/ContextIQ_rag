import { RootRedirect } from "@/components/auth/RouteGuards";

/** `/` → /chat (signed in) or /login (signed out). Plan §3. */
export default function Home() {
  return <RootRedirect />;
}
