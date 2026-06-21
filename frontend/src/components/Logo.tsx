// IndustryIQ wordmark: a small violet/indigo "IQ" glyph plus the name.
export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <div className="iq-grad grid h-8 w-8 place-items-center rounded-lg shadow-[0_0_18px_-4px_var(--color-accent)]">
        <span className="text-[13px] font-bold tracking-tight text-white">IQ</span>
      </div>
      {!compact && (
        <span className="text-[15px] font-semibold tracking-tight text-white">
          Industry<span className="text-accent-2">IQ</span>
        </span>
      )}
    </div>
  );
}
