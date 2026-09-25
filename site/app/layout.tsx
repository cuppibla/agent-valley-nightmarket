import type { Metadata } from "next";
import "./globals.css";

// The three faces of the valley, from Google Fonts at runtime — the same
// three every district uses. A stylesheet link rather than next/font so the
// static export builds anywhere, including a Cloud Shell with no way out.
const FONTS = "https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800;900&family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600&display=swap";

export const metadata: Metadata = {
  title: "Agent Valley · The Night Market",
  description: "Opens after dark. Everything at once, out loud, no second takes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href={FONTS} />
      </head>
      <body>{children}</body>
    </html>
  );
}
