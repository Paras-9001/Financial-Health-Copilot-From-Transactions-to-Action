import type { Metadata } from "next";
import { AuthProvider } from "@/components/auth-provider";
import { RecalculationProvider } from "@/components/recalculation-provider";
import "./globals.css";
export const metadata: Metadata = {
  title: "Financial Health Copilot",
  description:
    "Understand your financial position, see what may happen next, and test evidence-backed actions.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <RecalculationProvider>{children}</RecalculationProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
