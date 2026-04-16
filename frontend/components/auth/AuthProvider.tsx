"use client";

// 简单透传，认证逻辑由各页面自行处理
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
