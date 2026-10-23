import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SwarmCFO — finance team for one",
  description: "Five autonomous finance agents. One live world. One-tap Approve.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}