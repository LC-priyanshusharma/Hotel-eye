with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/App.tsx", "r") as f:
    content = f.read()

error_boundary = """
import React, { Component } from 'react';

class ErrorBoundary extends Component<any, any> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    this.setState({ errorInfo });
    console.error(error, errorInfo);
  }

  render() {
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
