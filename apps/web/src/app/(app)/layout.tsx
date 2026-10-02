"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BrandLockup } from "@/components/BrandLockup";
import { clearToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/clients", label: "Clients" },
  { href: "/assistant", label: "Advisor" },
  { href: "/settings/tally", label: "Settings" },
] as const;

function crumbs(pathname: string): { href?: string; label: string }[] {
  if (pathname.startsWith("/assistant")) {
    return [{ href: "/dashboard", label: "Dashboard" }, { label: "Advisor" }];
  }
  if (pathname.startsWith("/settings")) {
    return [{ href: "/dashboard", label: "Dashboard" }, { label: "Settings" }];
  }
  if (pathname.includes("/review")) {
    const parts = pathname.split("/");
    const clientId = parts[2];
    return [
      { href: "/clients", label: "Clients" },
      { href: `/clients/${clientId}`, label: "Client" },
      { label: "Review" },
    ];
  }
  if (pathname.includes("/upload")) {
    const parts = pathname.split("/");
    const clientId = parts[2];
    return [
      { href: "/clients", label: "Clients" },
      { href: `/clients/${clientId}`, label: "Client" },
      { label: "Upload" },
    ];
  }
  if (pathname.match(/^\/clients\/[^/]+$/)) {
    return [{ href: "/clients", label: "Clients" }, { label: "Workspace" }];
  }
  if (pathname.startsWith("/clients")) {
    return [{ label: "Clients" }];
  }
  return [{ label: "Dashboard" }];
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  const isAdvisor = pathname.startsWith("/assistant");
  const trail = crumbs(pathname);
  const maxW = "max-w-5xl";

  return (
    <div className={isAdvisor ? "flex h-dvh flex-col bg-void" : "min-h-screen bg-void"}>
      <header className="sticky top-0 z-20 shrink-0 border-b border-line bg-void/90 backdrop-blur-md">
        <div
          className={`mx-auto flex h-12 items-center justify-between gap-4 px-4 sm:px-6 ${isAdvisor ? "max-w-none" : maxW}`}
        >
          <div className="flex items-center gap-5">
            <BrandLockup compact href="/dashboard" />
            <nav className="hidden items-center gap-0.5 sm:flex">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  data-active={isActive(item.href)}
                  className="nav-link"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <button
            type="button"
            onClick={() => {
              clearToken();
              router.push("/login");
            }}
            className="text-xs font-medium text-ink-faint transition-colors hover:text-ink"
          >
            Sign out
          </button>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-line px-4 py-1.5 sm:hidden">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              data-active={isActive(item.href)}
              className="nav-link whitespace-nowrap"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      {isAdvisor ? (
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
      ) : (
        <>
          <div className={`mx-auto ${maxW} px-4 py-5 sm:px-6 sm:py-7`}>
            <nav
              aria-label="Breadcrumb"
              className="mb-4 flex flex-wrap items-center gap-1.5 text-xs text-ink-faint"
            >
              {trail.map((c, i) => (
                <span key={`${c.label}-${i}`} className="flex items-center gap-1.5">
                  {i > 0 && <span aria-hidden className="opacity-40">/</span>}
                  {c.href ? (
                    <Link href={c.href} className="hover:text-ink">
                      {c.label}
                    </Link>
                  ) : (
                    <span className="text-ink-muted">{c.label}</span>
                  )}
                </span>
              ))}
            </nav>
            <main className="work-sheet px-5 py-6 sm:px-8 sm:py-8">
              {children}
            </main>
          </div>
          <footer
            className={`mx-auto ${maxW} px-4 pb-8 text-center text-xs text-ink-faint sm:px-6`}
          >
            <a href="https://accountings.in" className="hover:text-ink">
              accountings.in
            </a>
            {" · "}
            <a
              href="https://www.trilolabs.com"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink"
            >
              A Trilolabs product
            </a>
          </footer>
        </>
      )}
    </div>
  );
}
