import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Personal AI Employee - Silver Tier",
  description: "AI-powered employee assistant with vault management and approval workflows",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
