import React, { useState } from 'react';
import ApiService from '../services/api';
import { useNavigate } from 'react-router-dom';
import { User, Lock, Loader2, ArrowRight } from 'lucide-react';

const Login = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({ account: '', password: '' });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleInputChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
        if (error) setError('');
    };

    const validateInput = () => {
        if (!formData.account.trim() || !formData.password.trim()) {
            setError('账号或密码不能为空');
            return false;
        }
        return true;
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!validateInput()) return;

        setIsLoading(true);

        try {
            const response = await ApiService.auth.login({
                account: formData.account,
                password: formData.password
            });

            localStorage.setItem('auth_token', response.token);
            localStorage.setItem('user_info', JSON.stringify(response.user));

            navigate('/dashboard');

        } catch (err) {
            setError(err.error || '登录失败，请稍后重试');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            <nav className="navbar">
                <div className="nav-brand">
                    <a href="https://www.xmkjzx.com/" className="nav-logo-link">
                        <div className="nav-logo-wrapper">
                            <img src="/logo.png" alt="Logo" className="nav-logo" />
                        </div>
                    </a>
                    <span>厦门大学附属科技中学翔安校区AIGC探索社</span>
                </div>
            </nav>

            <div className="app-container">
                <div className="login-card animate-fade-in">
                    <div className="text-center mb-8">
                        <h1 className="gradient-text">AIGC 探索社</h1>
                        <p className="subtitle">登录您的账户以继续</p>
                    </div>

                    <form onSubmit={handleLogin}>
                        <div className="form-group">
                            <div className="input-wrapper">
                                <User className="input-icon" size={20} />
                                <input
                                    type="text"
                                    name="account"
                                    placeholder="姓名 / 定位码"
                                    className="input-field"
                                    value={formData.account}
                                    onChange={handleInputChange}
                                    disabled={isLoading}
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <div className="input-wrapper">
                                <Lock className="input-icon" size={20} />
                                <input
                                    type="password"
                                    name="password"
                                    placeholder="密码"
                                    className="input-field"
                                    value={formData.password}
                                    onChange={handleInputChange}
                                    disabled={isLoading}
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="error-message">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="spin" size={20} />
                                    <span>验证中...</span>
                                </>
                            ) : (
                                <>
                                    <span>立即登录</span>
                                    <ArrowRight size={20} />
                                </>
                            )}
                        </button>
                    </form>
                    {/* Removed Forget Password Link */}
                </div>
            </div>
        </>
    );
};

export default Login;
