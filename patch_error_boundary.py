with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/App.tsx", "r") as f:
    content = f.read()

error_boundary = """
import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "20px", color: "white", backgroundColor: "black", height: "100vh", overflow: "auto" }}>
          <h1 style={{ color: "red" }}>Oops, React crashed!</h1>
          <p>Please take a screenshot of this error and send it to the agent:</p>
          <pre style={{ color: "lime", backgroundColor: "#222", padding: "10px" }}>
            {this.state.error?.toString()}
          </pre>
          <pre style={{ color: "pink", backgroundColor: "#222", padding: "10px" }}>
            {this.state.errorInfo?.componentStack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
"""

if "ErrorBoundary" not in content:
    content = content.replace("function App() {", error_boundary + "\nfunction App() {")
    content = content.replace("return (\n    <QueryClientProvider", "return (\n    <ErrorBoundary>\n    <QueryClientProvider")
    content = content.replace("    </QueryClientProvider>\n  )", "    </QueryClientProvider>\n    </ErrorBoundary>\n  )")

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/App.tsx", "w") as f:
    f.write(content)
