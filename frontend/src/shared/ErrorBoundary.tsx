import React, { Component, ReactNode } from "react";
import { Button, Typography } from "../lib/watercolor";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen w-full items-center justify-center p-6 bg-slate-50 dark:bg-[#082D4F]">
          <div className="max-w-md text-center space-y-4">
            <Typography variant="h5" className="text-[#103222] dark:text-[#F0F4F8]">
              页面加载遇到异常
            </Typography>
            <Typography variant="body2" color="textSecondary">
              系统遇到未预期的程序错误，请尝试刷新页面重试。
            </Typography>
            <div className="pt-2">
              <Button variant="primary" onClick={this.handleReload}>
                刷新页面
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
