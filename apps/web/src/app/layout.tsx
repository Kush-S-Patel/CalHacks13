import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SwarmCFO Claims — learns from a manager’s no",
  description:
    "Nonprofit reimbursement packages that ask, learn, improve next month, and prove every transition in audit.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}