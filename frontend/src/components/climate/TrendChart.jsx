import { useId, useMemo, useState } from 'react'

/**
 * One measure, over years. A line, because the question is a direction.
 *
 * Dependency-free SVG rather than a charting library: this is one series of at
 * most thirty points, and the smallest library that draws it is larger than the
 * rest of the application's own code.
 *
 * THE AXIS, WHICH IS WHERE A CHART LIKE THIS LIES
 *
 * A ten-year mean temperature moves by fractions of a degree. Fitted tightly to
 * its own range, 27.5 → 28.1 °C climbs off the top of the frame and reads as a
 * catastrophe; forced to a zero baseline it is a flat line and reads as nothing.
 * Neither is the truth.
 *
 * So the baseline is chosen by what the number *is*:
 *
 *   a total (rainfall)   → zero baseline. A sum is a ratio quantity; half the
 *                          bar means half the rain, and starting it anywhere
 *                          else breaks that.
 *   a mean (temperature) → a padded window around the data, which is the
 *                          convention for a temperature series and the only way
 *                          the shape is visible at all.
 *
 * And because a padded window *can* exaggerate, the change is printed as a
 * number beside the chart rather than left to the slope. The reader gets the
 * quantity, not just the picture of it.
 *
 * Colour is the theme's own primary and the theme's own tints, so dark mode is
 * automatic — there is no second palette here to keep in step.
 */

const PAD = { top: 14, right: 12, bottom: 26, left: 38 }
const HEIGHT = 168

export default function TrendChart({
  points,
  unit,
  zeroBaseline = false,
  label,
  emptyLabel,
}) {
  const gradientId = useId()
  const [active, setActive] = useState(null)

  const geometry = useMemo(() => {
    if (!points?.length) return null
    const values = points.map((point) => point.value)
    const lowest = Math.min(...values)
    const highest = Math.max(...values)

    let min
    let max
    if (zeroBaseline) {
      min = 0
      max = highest === 0 ? 1 : highest * 1.12
    } else {
      // A window around the data with real air above and below, so the line
      // never touches the frame and the eye is not told the range is the whole
      // story. A flat series still gets a band rather than dividing by zero.
      const span = highest - lowest || Math.max(Math.abs(highest) * 0.02, 1)
      min = lowest - span * 0.45
      max = highest + span * 0.45
    }

    const width = 320
    const plotWidth = width - PAD.left - PAD.right
    const plotHeight = HEIGHT - PAD.top - PAD.bottom
    const x = (index) =>
      PAD.left + (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth)
    const y = (value) => PAD.top + plotHeight - ((value - min) / (max - min)) * plotHeight

    return {
      width,
      min,
      max,
      x,
      y,
      plotHeight,
      coords: points.map((point, index) => ({ ...point, cx: x(index), cy: y(point.value) })),
      // Four gridlines is enough to read a value against and few enough to stay
      // recessive on a 390px screen.
      ticks: [0, 1, 2, 3].map((step) => {
        const value = min + ((max - min) * step) / 3
        return { value, y: y(value) }
      }),
    }
  }, [points, zeroBaseline])

  if (!geometry) {
    return (
      <div
        className="flex h-[168px] items-center justify-center rounded-[var(--radius-control)]
                   border border-dashed border-[rgb(var(--wx-tint)/0.22)] px-4 text-center"
      >
        <p className="text-[11.5px] leading-[1.45] text-muted">{emptyLabel}</p>
      </div>
    )
  }

  const { width, coords, ticks } = geometry
  const line = coords.map((point) => `${point.cx},${point.cy}`).join(' ')
  const area = `${PAD.left},${HEIGHT - PAD.bottom} ${line} ${coords[coords.length - 1].cx},${HEIGHT - PAD.bottom}`

  // Selective labels only: the ends, and the extremes when they are not the
  // ends. A number on every point is noise at this width.
  const highest = coords.reduce((a, b) => (b.value > a.value ? b : a))
  const lowest = coords.reduce((a, b) => (b.value < a.value ? b : a))
  const marked = new Set([coords[0].year, coords[coords.length - 1].year, highest.year, lowest.year])

  const decimals = unit === 'mm' ? 0 : 1

  return (
    <figure className="m-0 min-w-0">
      <svg
        viewBox={`0 0 ${width} ${HEIGHT}`}
        className="block h-auto w-full touch-manipulation"
        role="img"
        aria-label={label}
        onMouseLeave={() => setActive(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--wx-primary)" stopOpacity="0.20" />
            <stop offset="100%" stopColor="var(--wx-primary)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Grid and scale, recessive: they are there to read a value against,
            not to be looked at. */}
        {ticks.map((tick) => (
          <g key={tick.value}>
            <line
              x1={PAD.left}
              x2={width - PAD.right}
              y1={tick.y}
              y2={tick.y}
              stroke="rgb(var(--wx-tint) / 0.12)"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 6}
              y={tick.y + 3}
              textAnchor="end"
              fontSize="8.5"
              fill="var(--color-faint)"
            >
              {tick.value.toFixed(unit === 'mm' ? 0 : 1)}
            </text>
          </g>
        ))}

        <polyline points={area} fill={`url(#${gradientId})`} stroke="none" />
        <polyline
          points={line}
          fill="none"
          stroke="var(--wx-primary)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {coords.map((point, index) => {
          const isActive = active?.year === point.year
          return (
            <g key={point.year}>
              {/* A hit target far larger than the mark, because this is a
                  phone and the marks are 4px. */}
              <rect
                x={point.cx - 14}
                y={PAD.top}
                width="28"
                height={HEIGHT - PAD.top - PAD.bottom}
                fill="transparent"
                onMouseEnter={() => setActive(point)}
                onFocus={() => setActive(point)}
                onClick={() => setActive(isActive ? null : point)}
                tabIndex={0}
                role="button"
                aria-label={`${point.label}: ${point.value} ${unit}`}
                style={{ cursor: 'pointer', outline: 'none' }}
              />
              <circle
                cx={point.cx}
                cy={point.cy}
                r={isActive ? 4.5 : 3}
                fill="var(--wx-primary)"
                /* A 2px surface ring, so a marker over the area fill stays
                   legible in both themes. */
                stroke="var(--wx-surface)"
                strokeWidth="2"
              />
              {marked.has(point.year) && !isActive && (
                <text
                  /* The first and last labels are pushed inward. Centred, the
                     first one sat on top of the y-axis tick it was nearest and
                     the two numbers overprinted each other. */
                  x={point.cx + (index === 0 ? 4 : index === coords.length - 1 ? -4 : 0)}
                  y={point.cy - 8}
                  textAnchor={index === 0 ? 'start' : index === coords.length - 1 ? 'end' : 'middle'}
                  fontSize="8.5"
                  fontWeight="700"
                  fill="var(--color-ink-soft)"
                >
                  {point.value.toFixed(decimals)}
                </text>
              )}
            </g>
          )
        })}

        {/* X axis: the ends always, and the middle when there is room. Thirty
            year labels on a 390px screen is a grey smear. */}
        {coords.map((point, index) => {
          const step = Math.ceil(coords.length / 4)
          const show = index === 0 || index === coords.length - 1 || index % step === 0
          if (!show) return null
          return (
            <text
              key={`x-${point.year}`}
              x={point.cx}
              y={HEIGHT - 8}
              textAnchor={index === 0 ? 'start' : index === coords.length - 1 ? 'end' : 'middle'}
              fontSize="8.5"
              fill="var(--color-faint)"
            >
              {point.label}
            </text>
          )
        })}

        {active && (
          <line
            x1={active.cx}
            x2={active.cx}
            y1={PAD.top}
            y2={HEIGHT - PAD.bottom}
            stroke="var(--wx-primary)"
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity="0.55"
          />
        )}
      </svg>

      <figcaption className="mt-1.5 flex min-w-0 items-center justify-between gap-2 px-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-muted">
          {unit}
        </span>
        {active ? (
          <span className="text-[11px] font-bold tabular-nums text-ink">
            {active.label}: {active.value.toFixed(decimals)} {unit}
          </span>
        ) : (
          <span className="text-[10px] text-faint">{label}</span>
        )}
      </figcaption>

      {/* The same numbers as a table, so the series is readable without seeing
          it. One series needs no legend — the title above names it. */}
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr><th scope="col">Year</th><th scope="col">{unit}</th></tr>
        </thead>
        <tbody>
          {coords.map((point) => (
            <tr key={point.year}>
              <th scope="row">{point.label}</th>
              <td>{point.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}
