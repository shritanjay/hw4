/** Chat "thinking" indicator: a text-built Yale-style wordmark tile (serif "Yale" on Yale blue)
 *  with a light sweep and a status line. Pure HTML/CSS, no logo image. */
export default function YaleThinking({ label = 'Checking the shelves' }: { label?: string }) {
  return (
    <div className="yale-thinking" role="status" aria-label="Assistant is thinking">
      <span className="yale-tile" aria-hidden>
        Yale
      </span>
      <span className="yale-thinking-label">
        {label}
        <span className="ellipsis" aria-hidden>
          <span>.</span>
          <span>.</span>
          <span>.</span>
        </span>
      </span>
    </div>
  )
}
