# NemoClaw STR design system

Light beach UI for a short-term-rental operations agent (Sweet Clementine by the Sea,
Oceanside CA). Soft sky-blue and warm-sand surfaces, ONE sea-foam-green accent, serif display
with mono data. Build on the real components; do not reinvent their look.

## Setup
- The system is light by default. Put the app on the DS surface: the root element should
  carry `className="bg-background text-foreground"`. Tokens are defined in `styles.css` (`:root`).
- No provider is required. `LiveToggle` reads a context that has a safe default, so every
  component renders standalone.
- Body type is the serif (Fraunces). Use `font-mono` (JetBrains Mono) for numbers, ids,
  hashes, JSON, and code; `font-serif` for headings and prose.

## Styling idiom: Tailwind utility classes
Style with these token classes (all defined in `styles.css`), never raw hex:
- Surfaces: `bg-background` (page), `bg-card` (panel), `border-border` (hairline).
- Text: `text-foreground`, `text-muted-foreground`.
- The one accent is sea-foam green, used only where it carries meaning: `text-primary`,
  `bg-primary`, `border-primary`. A subtle tint is `bg-[hsl(var(--primary)/0.1)]`.
- Semantic colors only: `text-verified` / `border-verified` (emerald, success or verified)
  and `text-destructive` / `border-destructive` (red, critical or fault).
- Radius is near-zero: `rounded-[var(--radius)]`. No large radii, no per-category color
  pills, no glassmorphism, no gradients. Separate sections with whitespace and a hairline
  `Rule`, not with boxes (at most a few `Plate` or `Card` per view).

## Components
Primitives: `Button`, `Card` (with `CardHeader`, `CardTitle`, `CardDescription`,
`CardContent`, `CardFooter`), `Badge`, `Table` (with `TableHeader`, `TableBody`, `TableRow`,
`TableHead`, `TableCell`), `Tabs`, `Separator`, `Tooltip`, `Skeleton`, `Dialog`, `Progress`,
`Accordion`. Editorial vocabulary: `Stat` (big amber headline number, props label/value/sub),
`Plate` (the rare boxed surface), `StatusPill` (props ok/label), `Rule` (prop label),
`SectionLabel`, `EmptyState`, `ElapsedCounter` (live-call indicator),
`ProvenanceBadge` (LIVE/DEMO trust badge).

## Idiomatic example
```tsx
// components come from the NemoClaw STR library
<div className="bg-background text-foreground p-8">
  <Card>
    <CardHeader>
      <CardTitle className="font-serif">Sweet Clementine</CardTitle>
    </CardHeader>
    <CardContent className="flex flex-col gap-4">
      <Stat label="Management-fee overcharge" value="$84/mo" sub="22% vs 20% contract" />
      <Button>Approve correction</Button>
    </CardContent>
  </Card>
</div>
```

## Where the truth lives
Read `styles.css` (tokens) and each component's `<Name>.prompt.md` and `<Name>.d.ts` before
styling. Prop types are intentionally loose (the source has no published type tree); follow
the preview cards for real usage.
