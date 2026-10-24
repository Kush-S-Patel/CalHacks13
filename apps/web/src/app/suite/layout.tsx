import { SuiteNav } from "@/components/suite/SuiteNav";

export default function SuiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SuiteNav />
      {children}
    </>
  );
}