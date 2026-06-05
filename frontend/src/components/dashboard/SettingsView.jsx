import React, { useState, useEffect } from 'react';
import ApiService from '../../services/api';

import { Moon, Sun, Lock, Shield } from 'lucide-react';

const SettingsView = () => {
    // Initialize state from local storage or system preference
    const [darkMode, setDarkMode] = useState(() => {
        return localStorage.getItem('theme') === 'dark' ||
            (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    });

    const [passwords, setPasswords] = useState({
        current: '',
        new: '',
        confirm: ''
    });

    const handleUpdatePassword = async () => {
        if (!passwords.current || !passwords.new || !passwords.confirm) {
            alert('请填写所有字段');
            return;
        }
        if (passwords.new !== passwords.confirm) {
            alert('两次输入的新密码不一致');
            return;
        }

        try {
            const res = await ApiService.auth.changePassword({
                current_password: passwords.current,
                new_password: passwords.new
            });
            alert(res.message || '密码修改成功！');
            setPasswords({ current: '', new: '', confirm: '' });
        } catch (err) {
            alert(err.error || '修改失败');
        }
    };

    // Effect to apply theme instantly
    useEffect(() => {
        if (darkMode) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
        }
    }, [darkMode]);

    // Inline Styles
    const styles = {
        container: {
            animation: 'fadeIn 0.5s ease'
        },
        card: {
            backgroundColor: 'var(--bg-card)',
            borderRadius: '1rem',
            padding: '1.5rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
            marginBottom: '1.5rem',
            maxWidth: '600px',
            color: 'var(--text-primary)'
        },
        title: {
            fontSize: '1.125rem',
            fontWeight: 600,
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: 'var(--text-primary)'
        },
        row: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.5rem 0'
        },
        themeButton: {
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '0.5rem',
            backgroundColor: 'var(--bg-hover)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            cursor: 'pointer',
            fontWeight: 500,
            fontSize: '0.875rem',
            transition: 'all 0.2s'
        }
    };

    return (
        <div style={styles.container}>
            <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>系统设置</h2>

            <div style={styles.card}>
                <h3 style={styles.title}>
                    <Moon size={20} className="text-indigo-600" style={{ color: 'var(--primary-color)' }} />
                    外观设置
                </h3>
                <div style={styles.row}>
                    <span style={{ color: 'var(--text-primary)' }}>当前模式: {darkMode ? '深色' : '浅色'}</span>
                    <button
                        style={styles.themeButton}
                        onClick={() => setDarkMode(!darkMode)}
                        className="hover:opacity-80 active:scale-95"
                    >
                        {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                        {darkMode ? '切换浅色模式' : '切换深色模式'}
                    </button>
                </div>
            </div>

            <div style={styles.card}>
                <h3 style={styles.title}>
                    <Shield size={20} className="text-indigo-600" style={{ color: 'var(--primary-color)' }} />
                    账号安全
                </h3>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>当前密码</label>
                        <input
                            type="password"
                            className="input-field"
                            placeholder="输入当前密码"
                            value={passwords.current}
                            onChange={e => setPasswords({ ...passwords, current: e.target.value })}
                            style={{ backgroundColor: 'var(--bg-hover)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>新密码</label>
                        <input
                            type="password"
                            className="input-field"
                            placeholder="输入新密码"
                            value={passwords.new}
                            onChange={e => setPasswords({ ...passwords, new: e.target.value })}
                            style={{ backgroundColor: 'var(--bg-hover)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>确认新密码</label>
                        <input
                            type="password"
                            className="input-field"
                            placeholder="再次输入新密码"
                            value={passwords.confirm}
                            onChange={e => setPasswords({ ...passwords, confirm: e.target.value })}
                            style={{ backgroundColor: 'var(--bg-hover)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                        />
                    </div>
                    <div className="flex justify-end mt-4">
                        <button className="btn-primary" style={{ width: 'auto' }} onClick={handleUpdatePassword}>
                            <Lock size={18} />
                            更新密码
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsView;
