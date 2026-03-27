import type { ReactNode } from "react";

interface AppShellProps {
  header: ReactNode;
  sidebar: ReactNode;
  main: ReactNode;
  advanced: ReactNode;
}

export default function AppShell(props: AppShellProps) {
  const { header, sidebar, main, advanced } = props;
  return (
    <div className="min-h-screen px-4 py-5 md:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5">
        {header}
        <div className="grid gap-5 xl:grid-cols-[minmax(320px,0.4fr)_minmax(0,0.6fr)]">
          <aside className="flex flex-col gap-5">{sidebar}</aside>
          <main className="flex flex-col gap-5">{main}</main>
        </div>
        {advanced}
      </div>
    </div>
  );
}
