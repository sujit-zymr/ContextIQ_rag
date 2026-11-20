import { BotMessageSquare, FileText, Send } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/constants";

/**
 * Phase 1 placeholder: verifies the scaffold, theme tokens and shadcn/ui
 * components render correctly. Replaced in Phase 4/5 by the auth redirect
 * (`/` → `/chat` or `/login`).
 */
export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <BotMessageSquare className="size-6 text-primary" aria-hidden />
            <CardTitle className="text-xl tracking-tight">{APP_NAME}</CardTitle>
          </div>
          <CardDescription>{APP_DESCRIPTION}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-2">
            <Badge className="bg-success/15 text-success">Current</Badge>
            <Badge className="bg-warning/15 text-warning">Outdated</Badge>
            <Badge className="bg-destructive/15 text-destructive">Superseded</Badge>
            <Badge className="bg-info/15 text-info">Not yet effective</Badge>
            <Badge variant="secondary">
              <FileText aria-hidden /> Scaffold · Phase 1
            </Badge>
          </div>
          <div className="flex gap-2">
            <Input placeholder="Ask a question about your documents…" />
            <Button>
              <Send aria-hidden /> Send
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
