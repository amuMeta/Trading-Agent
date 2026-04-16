"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const particlesLoaded = useRef(false);

  // 初始化粒子效果
  useEffect(() => {
    // 已登录直接跳首页（用 router，不用 window.location）
    if (localStorage.getItem("isLoggedIn") === "true") {
      router.push("/");
      return;
    }

    if (particlesLoaded.current) return;
    particlesLoaded.current = true;

    const initParticles = () => {
      if ((window as any).particlesJS) {
        (window as any).particlesJS("particles-js", {
          particles: {
            number: { value: 70, density: { enable: true, value_area: 800 } },
            color: { value: "#3b82f6" },
            shape: { type: "circle" },
            opacity: { value: 0.45, random: false },
            size: { value: 3, random: true },
            line_linked: {
              enable: true,
              distance: 150,
              color: "#6366f1",
              opacity: 0.3,
              width: 1
            },
            move: {
              enable: true,
              speed: 1.5,
              direction: "none",
              random: false,
              straight: false,
              out_mode: "out",
              bounce: false
            }
          },
          interactivity: {
            detect_on: "canvas",
            events: {
              onhover: { enable: true, mode: "grab" },
              onclick: { enable: true, mode: "push" },
              resize: true
            },
            modes: {
              grab: { distance: 140, line_linked: { opacity: 1 } },
              push: { particles_nb: 3 }
            }
          },
          retina_detect: true
        });
      }
    };

    if ((window as any).particlesJS) {
      initParticles();
    } else {
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js";
      script.onload = initParticles;
      document.head.appendChild(script);
    }
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("请输入用户名和密码");
      return;
    }
    setError("");
    setLoading(true);

    setTimeout(() => {
      localStorage.setItem("isLoggedIn", "true");
      localStorage.setItem("username", username.trim());
      router.push("/");
    }, 800);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #eff6ff 0%, #ffffff 50%, #f5f3ff 100%)",
        overflow: "hidden"
      }}
    >
      {/* 粒子背景 */}
      <div
        id="particles-js"
        style={{ position: "absolute", inset: 0, zIndex: 0 }}
      />

      {/* 登录卡片容器 */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          width: "100%",
          maxWidth: "440px",
          padding: "0 24px"
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              boxShadow: "0 8px 32px rgba(59,130,246,0.4)",
              marginBottom: "16px"
            }}
          >
            <svg width="36" height="36" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <h1
            style={{
              fontSize: "32px",
              fontWeight: 700,
              background: "linear-gradient(135deg, #2563eb, #7c3aed)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              margin: 0
            }}
          >
            TradingAgents
          </h1>
          <p style={{ color: "#6b7280", marginTop: "8px", fontSize: "15px" }}>
            智能交易分析平台
          </p>
        </div>

        {/* 登录卡片 */}
        <div
          style={{
            background: "rgba(255,255,255,0.85)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            borderRadius: "24px",
            border: "1.5px solid rgba(229,231,235,0.8)",
            padding: "40px",
            boxShadow: "0 20px 60px rgba(0,0,0,0.08)"
          }}
        >
          <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#111827", marginBottom: "28px" }}>
            欢迎回来 👋
          </h2>

          <form onSubmit={handleLogin}>
            {/* 用户名 */}
            <div style={{ marginBottom: "20px" }}>
              <label
                htmlFor="username"
                style={{ display: "block", fontSize: "14px", fontWeight: 500, color: "#374151", marginBottom: "8px" }}
              >
                用户名
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => { setError(""); setUsername(e.target.value); }}
                placeholder="请输入用户名"
                autoComplete="username"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px 16px",
                  borderRadius: "12px",
                  border: "2px solid #e5e7eb",
                  fontSize: "15px",
                  color: "#111827",
                  background: "#fff",
                  outline: "none",
                  transition: "border-color 0.2s"
                }}
                onFocus={(e) => (e.target.style.borderColor = "#3b82f6")}
                onBlur={(e) => (e.target.style.borderColor = "#e5e7eb")}
              />
            </div>

            {/* 密码 */}
            <div style={{ marginBottom: "20px" }}>
              <label
                htmlFor="password"
                style={{ display: "block", fontSize: "14px", fontWeight: 500, color: "#374151", marginBottom: "8px" }}
              >
                密码
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => { setError(""); setPassword(e.target.value); }}
                placeholder="请输入密码"
                autoComplete="current-password"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px 16px",
                  borderRadius: "12px",
                  border: "2px solid #e5e7eb",
                  fontSize: "15px",
                  color: "#111827",
                  background: "#fff",
                  outline: "none",
                  transition: "border-color 0.2s"
                }}
                onFocus={(e) => (e.target.style.borderColor = "#3b82f6")}
                onBlur={(e) => (e.target.style.borderColor = "#e5e7eb")}
              />
            </div>

            {/* 错误提示 */}
            {error && (
              <div
                style={{
                  marginBottom: "16px",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  color: "#dc2626",
                  fontSize: "14px"
                }}
              >
                {error}
              </div>
            )}

            {/* 记住我 / 忘记密码 */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                <input type="checkbox" style={{ width: "16px", height: "16px", accentColor: "#3b82f6" }} />
                <span style={{ fontSize: "14px", color: "#6b7280" }}>记住我</span>
              </label>
              <a href="#" style={{ fontSize: "14px", color: "#3b82f6", textDecoration: "none" }}>
                忘记密码？
              </a>
            </div>

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                padding: "14px",
                borderRadius: "12px",
                border: "none",
                background: loading ? "#93c5fd" : "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                color: "#fff",
                fontSize: "16px",
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                boxShadow: "0 4px 20px rgba(59,130,246,0.4)",
                transition: "all 0.2s",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px"
              }}
            >
              {loading ? (
                <>
                  <span
                    style={{
                      display: "inline-block",
                      width: "18px",
                      height: "18px",
                      border: "2px solid rgba(255,255,255,0.4)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                      animation: "spin 0.7s linear infinite"
                    }}
                  />
                  登录中...
                </>
              ) : (
                "登 录"
              )}
            </button>
          </form>

          {/* 注册 */}
          <p style={{ textAlign: "center", marginTop: "24px", fontSize: "14px", color: "#6b7280" }}>
            还没有账号？{" "}
            <a href="#" style={{ color: "#3b82f6", fontWeight: 500, textDecoration: "none" }}>
              立即注册
            </a>
          </p>
        </div>

        {/* 底部版权 */}
        <p style={{ textAlign: "center", marginTop: "24px", fontSize: "13px", color: "#9ca3af" }}>
          © 2026 TradingAgents. All rights reserved.
        </p>
      </div>

      {/* 旋转动画 keyframes */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
