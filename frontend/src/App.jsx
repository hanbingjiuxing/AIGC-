import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import About from './pages/About';
import SplashScreen from './components/SplashScreen';
import { applyTheme, resolveInitialTheme } from './theme';

// Mock Protected Route - in a real app, this would check the token
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  // 开屏动画只在应用加载时播一次；结束后卸载，不干扰后续路由切换
  const [splashDone, setSplashDone] = useState(false);

  // 应用一挂载就把主题铺到 <html> 上：
  // 这样直接打开 /about、/login 也会是上次选的黑夜模式，
  // 不必等用户先访问一次系统设置。
  useEffect(() => {
    applyTheme(resolveInitialTheme());
  }, []);

  return (
    <Router>
      <div className="min-h-screen flex items-center justify-center p-4">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/about"
            element={
              <ProtectedRoute>
                <About />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>

      {!splashDone && <SplashScreen onDone={() => setSplashDone(true)} />}
    </Router>
  );
}

export default App;
