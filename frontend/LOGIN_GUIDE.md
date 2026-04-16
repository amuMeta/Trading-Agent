# 登录功能使用指南

## 🎯 功能概述

TradingAgents 平台现已集成完整的登录认证系统，包括：

- ✨ 精美的登录页面，带有粒子动画背景效果
- 🔐 用户认证和会话管理
- 🚪 自动重定向（未登录用户访问受保护页面会跳转到登录页）
- 👤 用户信息显示和登出功能

## 📱 登录页面特性

### 视觉设计
- **粒子动画背景**：使用 particles.js 创建动态粒子效果
- **渐变色彩**：蓝色到紫色的渐变主题
- **毛玻璃效果**：登录卡片使用 backdrop-blur 实现半透明效果
- **流畅动画**：淡入动画和交互反馈

### 交互功能
- 用户名和密码输入
- 记住我选项
- 忘记密码链接（占位）
- 注册链接（占位）
- 加载状态显示
- 错误提示

## 🔑 使用方法

### 1. 访问登录页面

直接访问：`http://localhost:3000/login`

或者访问任何受保护的页面，系统会自动重定向到登录页。

### 2. 登录

**当前版本为演示模式，任何非空的用户名和密码都可以登录。**

示例：
- 用户名：`admin`
- 密码：`123456`

点击"登录"按钮后，系统会：
1. 显示加载状态
2. 验证输入（非空检查）
3. 保存登录状态到 localStorage
4. 自动跳转到首页

### 3. 登出

在任何页面的右上角，点击"退出登录"按钮即可登出。

登出后会：
1. 清除 localStorage 中的登录信息
2. 自动跳转回登录页

## 🛡️ 受保护的页面

以下页面需要登录后才能访问：

- `/` - 首页（主分析页面）
- `/history` - 历史会话页面
- `/analysis/[sessionId]` - 分析详情页面

## 🔧 技术实现

### 认证流程

```
用户访问 → 检查 localStorage → 
  ├─ 已登录 → 允许访问
  └─ 未登录 → 重定向到 /login
```

### 状态管理

使用 `localStorage` 存储：
- `isLoggedIn`: 登录状态（"true" / null）
- `username`: 用户名

### 中间件

`middleware.ts` 提供服务端路由保护（可选）

### 客户端保护

每个受保护的页面在 `useEffect` 中检查登录状态：

```typescript
useEffect(() => {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  if (isLoggedIn !== "true") {
    router.push("/login");
  }
}, [router]);
```

## 🎨 自定义配置

### 修改粒子效果

在 `frontend/app/login/page.tsx` 中找到 `particlesJS` 配置：

```javascript
particlesJS("particles-js", {
  particles: {
    number: { value: 80 },  // 粒子数量
    color: { value: "#3b82f6" },  // 粒子颜色
    // ... 更多配置
  }
});
```

### 修改登录验证

在 `handleLogin` 函数中添加实际的 API 调用：

```typescript
const handleLogin = async (e: React.FormEvent) => {
  e.preventDefault();
  setLoading(true);
  
  try {
    // 调用后端 API
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem("isLoggedIn", "true");
      localStorage.setItem("username", username);
      localStorage.setItem("token", data.token);
      router.push("/");
    } else {
      setError("用户名或密码错误");
    }
  } catch (error) {
    setError("登录失败，请稍后重试");
  } finally {
    setLoading(false);
  }
};
```

## 🚀 后续改进建议

### 安全性增强
1. **JWT Token**：使用 JWT 替代 localStorage 的简单标记
2. **HTTP-Only Cookies**：将 token 存储在 HTTP-only cookies 中
3. **Token 刷新**：实现 token 自动刷新机制
4. **密码加密**：前端发送前对密码进行哈希处理

### 功能扩展
1. **注册功能**：实现用户注册流程
2. **忘记密码**：添加密码重置功能
3. **第三方登录**：集成 OAuth（Google, GitHub 等）
4. **多因素认证**：添加 2FA 支持
5. **会话管理**：显示活跃会话，支持远程登出

### 用户体验
1. **记住我**：实现真正的"记住我"功能
2. **自动登录**：Token 有效期内自动登录
3. **登录历史**：显示最近登录记录
4. **密码强度检测**：注册时检测密码强度

## 📝 文件结构

```
frontend/
├── app/
│   ├── login/
│   │   └── page.tsx          # 登录页面
│   ├── page.tsx               # 首页（带登录检查）
│   ├── history/
│   │   └── page.tsx          # 历史页面（带登录检查）
│   └── analysis/
│       └── [sessionId]/
│           └── page.tsx      # 详情页面（带登录检查）
├── components/
│   └── layout/
│       └── Header.tsx        # 头部组件（带用户信息和登出）
├── middleware.ts             # 路由中间件
└── app/globals.css           # 全局样式（含登录页动画）
```

## 🎉 完成状态

- ✅ 登录页面设计
- ✅ 粒子动画背景
- ✅ 用户认证逻辑
- ✅ 路由保护
- ✅ 用户信息显示
- ✅ 登出功能
- ✅ 自动重定向
- ✅ 响应式设计
- ✅ 加载状态
- ✅ 错误处理

## 📞 支持

如需帮助或有任何问题，请查看项目文档或联系开发团队。
