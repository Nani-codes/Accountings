import Link from "next/link";

export function BrandLockup({ compact, href = "/" }: { compact?: boolean; href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2 font-bold text-lg">
      <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded" />
      {!compact && <span>Accountings</span>}
    </Link>
  );
}
