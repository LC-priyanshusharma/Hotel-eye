with open("/home/user/LogicEye-main/frontend/src/App.tsx", "r") as f:
    content = f.read()

content = content.replace("<ErrorBoundary>\n    <QueryClientProvider", "<QueryClientProvider")
content = content.replace("</QueryClientProvider>\n    </ErrorBoundary>", "</QueryClientProvider>")
import re
content = re.sub(r'import React, { Component, ErrorInfo, ReactNode } from "react";.*?class ErrorBoundary extends Component<Props, State> {.*?}\n\n', '', content, flags=re.DOTALL)

with open("/home/user/LogicEye-main/frontend/src/App.tsx", "w") as f:
    f.write(content)
