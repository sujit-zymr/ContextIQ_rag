import type { Metadata } from "next";
import { DM_Sans, Geist_Mono } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/constants";

import { Providers } from "./providers";

import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: APP_NAME,
    template: `%s · ${APP_NAME}`,
  },
  description: APP_DESCRIPTION,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // Light by default; Providers (next-themes) adds the `dark` class when chosen.
    // suppressHydrationWarning: next-themes sets the class before React loads.
    <html
      lang="en"
      className={`${dmSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      {/* Browser extensions add attributes to <body> (e.g. contenteditable) before
          React loads; this ignores <body>'s own attributes only, not its children. */}
      <body className="flex min-h-full flex-col" suppressHydrationWarning>
        <Providers>
          <TooltipProvider>{children}</TooltipProvider>
          {/* Inside Providers: the toaster follows the current theme. */}
          <Toaster position="top-right" richColors closeButton />
        </Providers>
      </body>
    </html>
  );
}
