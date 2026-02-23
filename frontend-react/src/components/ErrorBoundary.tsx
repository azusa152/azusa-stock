import { Component, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import i18n from "@/lib/i18n"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : String(error)
    return { hasError: true, message }
  }

  handleRetry = () => {
    this.setState({ hasError: false, message: "" })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center gap-4 p-8 text-center">
          <p className="text-4xl">⚠️</p>
          <p className="text-sm font-medium text-destructive">{i18n.t("common.error_render")}</p>
          {this.state.message && (
            <p className="text-xs text-muted-foreground max-w-sm">{this.state.message}</p>
          )}
          <Button size="sm" variant="outline" onClick={this.handleRetry}>
            {i18n.t("common.retry")}
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
