export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-4 px-6">
      <p className="text-sm text-ink-muted">GST Workbench</p>
      <h1 className="text-3xl font-bold tracking-tight text-ash-bright">
        AI GST Reconciliation
      </h1>
      <p className="max-w-prose text-ink-muted">
        Upload GST data. Find mismatches. Generate client follow-ups. Finish the
        review faster.
      </p>
      <a
        href="/login"
        className="inline-flex h-10 w-fit items-center rounded-pill bg-cta px-4 text-sm font-medium text-cta-ink"
      >
        Continue
      </a>
    </main>
  );
}
