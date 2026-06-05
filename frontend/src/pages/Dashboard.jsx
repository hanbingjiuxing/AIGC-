import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Image, Settings, LogOut, LayoutDashboard, Users, CalendarCheck } from 'lucide-react';
import ProfileView from '../components/dashboard/ProfileView';
import WorksView from '../components/dashboard/WorksView';
import SettingsView from '../components/dashboard/SettingsView';
import MemberManagementView from '../components/dashboard/MemberManagementView';
import AttendanceView from '../components/dashboard/AttendanceView';

const Dashboard = () => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('profile');
    const user = JSON.parse(localStorage.getItem('user_info') || '{}');
    const isPrivileged = user.role === 'teacher' || user.role === 'president';

    const handleLogout = () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        navigate('/login');
    };

    const renderContent = () => {
        switch (activeTab) {
            case 'profile': return <ProfileView />;
            case 'works': return <WorksView />;
            case 'settings': return <SettingsView />;
            case 'members': return <MemberManagementView />;
            case 'attendance': return <AttendanceView />;
            default: return <ProfileView />;
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

            <div className="dashboard-layout">
                {/* Sidebar */}
                <aside className="sidebar">
                    <div className="px-4 mb-4">
                        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">菜单</p>
                    </div>

                    <nav className="space-y-1">
                        <a
                            onClick={() => setActiveTab('profile')}
                            className={`nav-item ${activeTab === 'profile' ? 'active' : ''}`}
                        >
                            <User size={20} />
                            <span>个人信息</span>
                        </a>
                        <a
                            onClick={() => setActiveTab('works')}
                            className={`nav-item ${activeTab === 'works' ? 'active' : ''}`}
                        >
                            <Image size={20} />
                            <span>作品管理</span>
                        </a>
                        <a
                            onClick={() => setActiveTab('attendance')}
                            className={`nav-item ${activeTab === 'attendance' ? 'active' : ''}`}
                        >
                            <CalendarCheck size={20} />
                            <span>每日签到</span>
                        </a>
                        {isPrivileged && (
                            <a
                                onClick={() => setActiveTab('members')}
                                className={`nav-item ${activeTab === 'members' ? 'active' : ''}`}
                            >
                                <Users size={20} />
                                <span>成员管理</span>
                            </a>
                        )}

                        <a
                            onClick={() => setActiveTab('settings')}
                            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
                        >
                            <Settings size={20} />
                            <span>系统设置</span>
                        </a>
                    </nav>

                    <div className="mt-auto pt-4 border-t border-gray-100">
                        <a onClick={handleLogout} className="nav-item text-red-500 hover:bg-red-50 hover:text-red-600">
                            <LogOut size={20} />
                            <span>退出登录</span>
                        </a>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="main-content">
                    {renderContent()}
                </main>
            </div>
        </>
    );
};

export default Dashboard;
