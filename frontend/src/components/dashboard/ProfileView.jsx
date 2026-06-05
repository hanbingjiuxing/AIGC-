import React, { useState, useEffect } from 'react';
import ApiService from '../../services/api';
import { Settings, Calendar, Bell, ChevronRight, Hash, GraduationCap, Plus, Edit2, Trash2, X, Save } from 'lucide-react';

const ProfileView = () => {
    const user = JSON.parse(localStorage.getItem('user_info') || '{}');
    const canManage = user.role === 'teacher' || user.role === 'president';

    const [profile] = useState({
        name: user.name || '李文',
        studentId: user.studentId || '20230101',
        class: user.class || '2023级 计算机一班',
        role: user.role || '普通社员',
        joinDate: user.createdAt || new Date().toISOString().split('T')[0],
    });

    // Calculate days since join
    const getDaysSinceJoin = () => {
        if (!profile.joinDate) return 0;
        const joinDate = new Date(profile.joinDate);
        const today = new Date();
        const diffTime = Math.abs(today - joinDate);
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    };

    const [announcements, setAnnouncements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingAnn, setEditingAnn] = useState(null);
    const [formData, setFormData] = useState({ title: '', content: '', tag: '通知' });

    const fetchAnnouncements = async () => {
        try {
            const data = await ApiService.announcements.list();
            setAnnouncements(data.announcements || []);
        } catch (err) {
            console.error('Failed to fetch announcements:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnnouncements();
    }, []);

    const openCreateModal = () => {
        setEditingAnn(null);
        setFormData({ title: '', content: '', tag: '通知' });
        setModalOpen(true);
    };

    const openEditModal = (ann) => {
        setEditingAnn(ann);
        setFormData({ title: ann.title, content: ann.content || '', tag: ann.tag });
        setModalOpen(true);
    };

    const handleSave = async () => {
        try {
            if (editingAnn) {
                await ApiService.announcements.update(editingAnn.id, formData);
            } else {
                await ApiService.announcements.create(formData);
            }
            setModalOpen(false);
            fetchAnnouncements();
        } catch (err) {
            alert(err.error || '操作失败');
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('确定要删除这条公告吗？')) return;
        try {
            await ApiService.announcements.delete(id);
            fetchAnnouncements();
        } catch (err) {
            alert(err.error || '删除失败');
        }
    };

    // Inline styles using CSS variables for Dark Mode support
    const styles = {
        cardFlex: {
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'stretch',
            padding: 0,
            overflow: 'hidden',
            backgroundColor: 'var(--bg-card)',
            color: 'var(--text-primary)',
            borderRadius: '1rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
        },
        leftCol: {
            width: '35%',
            backgroundColor: 'var(--bg-hover)',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            borderRight: '1px solid var(--border-color)'
        },
        rightCol: {
            width: '65%',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            backgroundColor: 'var(--bg-card)'
        },
        avatar: {
            width: '8rem',
            height: '8rem',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #6366f1, #a855f7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '2.5rem',
            fontWeight: 'bold',
            marginBottom: '1rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
        },
        roleBadge: {
            padding: '0.375rem 1rem',
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            color: '#6366f1',
            borderRadius: '9999px',
            fontSize: '0.875rem',
            fontWeight: 600,
            marginBottom: '1.5rem'
        },
        divider: {
            width: '100%',
            borderTop: '1px solid var(--border-color)',
            paddingTop: '1rem',
        },
        infoRow: {
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '0.875rem',
            marginBottom: '0.75rem',
            width: '100%'
        },
        infoBox: {
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1rem',
            marginBottom: '1rem',
            transition: 'all 0.2s',
            backgroundColor: 'var(--bg-card)'
        },
        iconBox: {
            padding: '0.75rem',
            borderRadius: '0.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        },
        announcementCard: {
            backgroundColor: 'var(--bg-card)',
            color: 'var(--text-primary)',
            padding: '1.5rem',
            borderRadius: '1rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
        },
        modalOverlay: {
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 50,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem'
        },
        modalCard: {
            backgroundColor: 'var(--bg-card)',
            color: 'var(--text-primary)',
            padding: '1.5rem',
            borderRadius: '1rem',
            width: '100%',
            maxWidth: '500px',
            border: '1px solid var(--border-color)'
        }
    };

    const getRoleDisplay = (role) => {
        switch (role) {
            case 'teacher': return '指导老师';
            case 'president': return '社长';
            default: return '普通社员';
        }
    };

    return (
        <div className="animate-fade-in space-y-6">
            <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>个人信息</h2>

            {/* Profile Card */}
            <div style={styles.cardFlex}>
                {/* Left Side */}
                <div style={styles.leftCol}>
                    <div style={styles.avatar}>
                        {profile.name[0]}
                    </div>
                    <h3 className="text-2xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>{profile.name}</h3>
                    <span style={styles.roleBadge}>
                        {getRoleDisplay(profile.role)}
                    </span>

                    <div style={styles.divider}>
                        <div style={styles.infoRow}>
                            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <GraduationCap size={16} /> 班级
                            </span>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{profile.class}</span>
                        </div>
                        <div style={styles.infoRow}>
                            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Hash size={16} /> 学号
                            </span>
                            <span style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--text-primary)' }}>{profile.studentId}</span>
                        </div>
                    </div>
                </div>

                {/* Right Side */}
                <div style={styles.rightCol}>
                    <h4 className="text-sm font-bold uppercase tracking-wider mb-6" style={{ color: 'var(--text-secondary)' }}>详细资料</h4>

                    {/* Stats Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                        <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: 'var(--bg-hover)', borderRadius: '0.75rem' }}>
                            <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#6366f1' }}>{getDaysSinceJoin()}</p>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>加入天数</p>
                        </div>
                        <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: 'var(--bg-hover)', borderRadius: '0.75rem' }}>
                            <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#10b981' }}>--</p>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>提交作品</p>
                        </div>
                        <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: 'var(--bg-hover)', borderRadius: '0.75rem' }}>
                            <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#f59e0b' }}>--</p>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>签到次数</p>
                        </div>
                    </div>

                    <div>
                        {/* Join Date Card */}
                        <div style={styles.infoBox}>
                            <div style={{ ...styles.iconBox, backgroundColor: 'rgba(234, 88, 12, 0.1)', color: '#ea580c' }}>
                                <Calendar size={24} />
                            </div>
                            <div style={{ flex: 1 }}>
                                <p className="text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>加入时间</p>
                                <div className="flex items-center justify-between">
                                    <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{profile.joinDate}</p>
                                    <span style={{ backgroundColor: 'rgba(234, 88, 12, 0.1)', color: '#ea580c', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 500 }}>活跃成员</span>
                                </div>
                            </div>
                        </div>

                        {/* Account Status Card */}
                        <div style={styles.infoBox}>
                            <div style={{ ...styles.iconBox, backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
                                <Settings size={24} />
                            </div>
                            <div style={{ flex: 1 }}>
                                <p className="text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>账号状态</p>
                                <div className="flex items-center justify-between">
                                    <p className="text-xl font-bold" style={{ color: '#10b981' }}>正常</p>
                                    <span style={{ backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#10b981', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 500 }}>已验证</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Announcements */}
            <div style={styles.announcementCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)', fontWeight: 600, fontSize: '1.1rem' }}>
                        <Bell size={20} className="text-amber-500" />
                        社团公告
                    </h3>
                    {canManage && (
                        <button
                            onClick={openCreateModal}
                            className="btn-primary"
                            style={{ width: 'auto', padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                        >
                            <Plus size={16} />
                            新增公告
                        </button>
                    )}
                </div>
                <div>
                    {loading ? (
                        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem' }}>加载中...</p>
                    ) : announcements.length === 0 ? (
                        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem' }}>暂无公告</p>
                    ) : (
                        announcements.map((item) => (
                            <div
                                key={item.id}
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '0.75rem',
                                    borderBottom: '1px solid var(--border-color)',
                                }}
                                className="hover:bg-gray-50/5 transition-colors"
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                                    <span style={{
                                        padding: '0.125rem 0.5rem',
                                        borderRadius: '0.25rem',
                                        fontSize: '0.75rem',
                                        backgroundColor: item.tag === '活动' ? 'rgba(220, 38, 38, 0.1)' : item.tag === '通知' ? 'rgba(37, 99, 235, 0.1)' : 'var(--bg-hover)',
                                        color: item.tag === '活动' ? '#dc2626' : item.tag === '通知' ? '#2563eb' : 'var(--text-secondary)'
                                    }}>
                                        {item.tag}
                                    </span>
                                    <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                        {item.title}
                                    </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item.date}</span>
                                    {canManage && (
                                        <>
                                            <button
                                                onClick={() => openEditModal(item)}
                                                style={{ padding: '0.25rem', color: 'var(--text-secondary)', background: 'none', border: 'none', cursor: 'pointer' }}
                                                title="编辑"
                                            >
                                                <Edit2 size={16} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(item.id)}
                                                style={{ padding: '0.25rem', color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}
                                                title="删除"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </>
                                    )}
                                    {!canManage && <ChevronRight size={16} style={{ color: 'var(--text-secondary)' }} />}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Create/Edit Modal */}
            {modalOpen && (
                <div style={styles.modalOverlay}>
                    <div style={styles.modalCard}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h3 className="text-xl font-bold">{editingAnn ? '编辑公告' : '新增公告'}</h3>
                            <button onClick={() => setModalOpen(false)} style={{ color: 'var(--text-secondary)', background: 'none', border: 'none', cursor: 'pointer' }}>
                                <X size={24} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">标题</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="公告标题"
                                    value={formData.title}
                                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">内容</label>
                                <textarea
                                    className="input-field"
                                    placeholder="公告内容（可选）"
                                    rows={3}
                                    value={formData.content}
                                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    style={{ resize: 'vertical' }}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">标签</label>
                                <select
                                    className="input-field"
                                    value={formData.tag}
                                    onChange={(e) => setFormData({ ...formData, tag: e.target.value })}
                                >
                                    <option value="通知">通知</option>
                                    <option value="活动">活动</option>
                                    <option value="必读">必读</option>
                                </select>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setModalOpen(false)}
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-card)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer'
                                }}
                            >
                                取消
                            </button>
                            <button
                                className="btn-primary"
                                style={{ width: 'auto' }}
                                onClick={handleSave}
                            >
                                <Save size={16} />
                                保存
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProfileView;
