import { Component } from 'react'

/**
 * Last line of defence.
 *
 * A render error in one panel would otherwise blank the whole app; this turns
 * it into an on-brand message with a way out. The details stay in the console
 * for a developer and never reach the user as a stack trace.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error, info) {
    console.error('WeatherGPT render error:', error, info)
  }

  render() {
    if (!this.state.failed) return this.props.children

    return (
      <div className="flex min-h-dvh items-center justify-center p-6">
        <div className="glass max-w-md p-6 text-center">
          <p className="text-2xl" aria-hidden="true">◈</p>
          <h1 className="mt-3 text-lg font-semibold text-ink">Something went wrong</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            WeatherGPT hit an unexpected problem while drawing this screen. Reloading usually clears it.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-5 rounded-[var(--radius-pill)] bg-primary px-5 py-2.5 text-sm font-semibold text-[#04121d]"
          >
            Reload
          </button>
        </div>
      </div>
    )
  }
}
