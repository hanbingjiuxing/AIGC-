
import React, { useState, useEffect } from 'react';
import ApiService from '../../services/api';
import { Search, UserPlus, MoreHorizontal, Shield, Key, UserX, Edit2, Save, X, ChevronDown, Image as ImageIcon } from 'lucide-react';
import MemberWorksModal from './MemberWorksModal';

const MemberManagementView = () => {
    const currentUser = JSON.parse(localStorage.getItem('user_info') || '{}');
    const isTeacher = currentUser.role === 'teacher';
    console.log('Current User:', currentUser);
    console.log('Is Teacher:', isTeacher);

    const [members, setMembers] = useState([]);
    const [loading, setLoading] = useState(false);

    // Form states
    const [newName, setNewName] = useState('');
    const [newStudentId, setNewStudentId] = useState('');
    const [newClass, setNewClass] = useState('');

    const [searchTerm, setSearchTerm] = useState('');
    const [modalOpen, setModalOpen] = useState(false);
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [worksModalOpen, setWorksModalOpen] = useState(false);
    const [selectedMember, setSelectedMember] = useState(null);
    const [roleDropdownOpen, setRoleDropdownOpen] = useState(false);
    const [newMemberRole, setNewMemberRole] = useState('student');

    const fetchMembers = async () => {
        setLoading(true);
        try {
            const data = await ApiService.members.list({ search: searchTerm });
            console.log('API Members Response:', data);
            if (data && Array.isArray(data.members)) {
                setMembers(data.members);
            } else {
                console.error('Invalid members data format:', data);
                setMembers([]);
            }
        } catch (err) {
            console.error('Failed to fetch members:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMembers();
    }, [searchTerm]);

    const roleOptions = [
        { value: 'student', label: '普通社员 (Student)' },
        { value: 'teacher', label: '指导老师 (Teacher)' },
        { value: 'president', label: '社长 (President)' }
    ];

    // CSS Variables based styles
    const styles = {
        container: { animation: 'fadeIn 0.5s ease', color: 'var(--text-primary)' },
        card: {
            backgroundColor: 'var(--bg-card)',
            borderRadius: '1rem',
            padding: '1.5rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
        },
        header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
        tableHeader: {
            display: 'grid',
            gridTemplateColumns: 'minmax(200px, 2fr) 1fr 1.5fr 1fr 1fr 1fr',
            padding: '1rem',
            backgroundColor: 'var(--bg-hover)',
            borderBottom: '1px solid var(--border-color)',
            fontSize: '0.875rem',
            fontWeight: 600,
            color: 'var(--text-secondary)'
        },
        tableRow: {
            display: 'grid',
            gridTemplateColumns: 'minmax(200px, 2fr) 1fr 1.5fr 1fr 1fr 1fr',
            padding: '1rem',
            borderBottom: '1px solid var(--border-color)',
            alignItems: 'center',
            transition: 'background-color 0.2s',
            cursor: 'default'
        },
        badge: (role) => ({
            padding: '0.25rem 0.75rem',
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: 500,
            backgroundColor: role === 'president' ? 'rgba(99, 102, 241, 0.1)' : 'rgba(100, 116, 139, 0.1)',
            color: role === 'president' ? '#6366f1' : '#64748b'
        }),
        statusDot: (status) => ({
            height: '0.5rem',
            width: '0.5rem',
            borderRadius: '50%',
            backgroundColor: status === 'online' ? '#10b981' : '#cbd5e1',
            display: 'inline-block',
            marginRight: '0.5rem'
        }),
        actionBtn: {
            padding: '0.5rem',
            borderRadius: '0.375rem',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.2s',
            border: 'none',
            background: 'transparent',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        }
    };

    const handleEdit = (member) => {
        setSelectedMember(member);
        setEditModalOpen(true);
    };

    const handleViewWorks = (member) => {
        setSelectedMember(member);
        setWorksModalOpen(true);
    };

    const handleCreate = async () => {
        try {
            await ApiService.members.create({
                name: newName,
                studentId: newStudentId,
                class: newClass,
                role: newMemberRole
            });
            setModalOpen(false);
            // Reset form
            setNewName('');
            setNewStudentId('');
            setNewClass('');
            setNewMemberRole('student');

            fetchMembers();
            alert('成员创建成功');
        } catch (err) {
            alert(err.error || '创建失败');
        }
    };

    const handleResetPassword = async (id) => {
        if (!window.confirm('确定要重置该成员的密码吗？密码将重置为学号。')) return;
        try {
            const res = await ApiService.members.resetPassword(id);
            alert(res.message);
        } catch (err) {
            alert(err.error || '操作失败');
        }
    };

    const handleKick = async (id) => {
        if (!window.confirm('确定要注销该成员吗？')) return;
        try {
            await ApiService.members.delete(id);
            fetchMembers();
            alert('成员已注销');
        } catch (err) {
            alert(err.error || '操作失败');
        }
    };

    const handleUpdate = async () => {
        if (!selectedMember) return;
        try {
            await ApiService.members.update(selectedMember.id, {
                name: newName,
                studentId: newStudentId,
                class: newClass,
                role: newMemberRole
            });
            setEditModalOpen(false);
            // Reset form
            setNewName('');
            setNewStudentId('');
            setNewClass('');
            setNewMemberRole('student');
            setSelectedMember(null);

            fetchMembers();
            alert('成员信息更新成功');
        } catch (err) {
            alert(err.error || '更新失败');
        }
    };

    useEffect(() => {
        if (selectedMember && editModalOpen) {
            setNewName(selectedMember.name || '');
            setNewStudentId(selectedMember.studentId || '');
            setNewClass(selectedMember.class || '');
            setNewMemberRole(selectedMember.role || 'student');
        } else if (!editModalOpen && !modalOpen) {
            // Reset only when both modals are closed
            setNewName('');
            setNewStudentId('');
            setNewClass('');
            setNewMemberRole('student');
        }
    }, [selectedMember, editModalOpen]);

    // Robust filter
    // Ensure we handle case where member properties might be null
    // Also filter out the teacher from the list
    const filteredMembers = (Array.isArray(members) ? members : [])
        .filter(m => m.role === 'student' || m.role === 'president');

    return (
        <div style={styles.container}>
            {/* Header */}
            <div style={styles.header}>
                <div>
                    <h2 className="text-2xl font-bold">成员管理</h2>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                        共 {filteredMembers.length} 位成员
                    </p>
                </div>
                {isTeacher && (
                    <button
                        className="btn-primary"
                        style={{ width: 'auto' }}
                        onClick={() => setModalOpen(true)}
                    >
                        <UserPlus size={18} />
                        新增成员
                    </button>
                )}
            </div>

            {/* Toolbar */}
            <div style={{ ...styles.card, padding: '1rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem' }}>
                <div style={{ position: 'relative', flex: 1 }}>
                    <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                    <input
                        type="text"
                        placeholder="搜索姓名或学号..."
                        className="input-field"
                        style={{ paddingLeft: '2.5rem', backgroundColor: 'var(--bg-hover)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* Member List */}
            <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
                <div style={styles.tableHeader}>
                    <div>成员信息</div>
                    <div>学号</div>
                    <div>班级</div>
                    <div>身份</div>
                    <div>状态</div>
                    {/* Action column is for Teacher OR President (Teacher gets full controls, President gets View Works) */}
                    {(isTeacher || currentUser.role === 'president') && <div className="text-right">操作</div>}
                </div>

                {filteredMembers.map(member => (
                    <div key={member.id} style={styles.tableRow} className="hover:bg-gray-50/5">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-sm">
                                {(member.name || '?')[0]}
                            </div>
                            <span className="font-medium">{member.name || 'Unknown'}</span>
                        </div>
                        <div className="font-mono text-sm">{member.studentId || '-'}</div>
                        <div className="text-sm">{member.class || '-'}</div>
                        <div>
                            <span style={styles.badge(member.role || 'student')}>
                                {member.role === 'president' ? '社长' : '成员'}
                            </span>
                        </div>
                        <div className="flex items-center text-sm">
                            <span style={styles.statusDot(member.status || 'offline')}></span>
                            {member.status === 'online' ? '在线' : '离线'}
                        </div>

                        {(isTeacher || currentUser.role === 'president') && (
                            <div className="flex justify-end gap-1">
                                <button title="查看作品" style={styles.actionBtn} onClick={() => handleViewWorks(member)}>
                                    <ImageIcon size={18} />
                                </button>

                                {isTeacher && (
                                    <>
                                        <button title="编辑信息" style={styles.actionBtn} onClick={() => handleEdit(member)}>
                                            <Edit2 size={18} />
                                        </button>
                                        <button title="重置密码" style={styles.actionBtn} onClick={() => handleResetPassword(member.id)}>
                                            <Key size={18} />
                                        </button>
                                        <button title="注销成员" style={{ ...styles.actionBtn, color: '#ef4444' }} onClick={() => handleKick(member.id)}>
                                            <UserX size={18} />
                                        </button>
                                    </>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <MemberWorksModal
                isOpen={worksModalOpen}
                onClose={() => setWorksModalOpen(false)}
                member={selectedMember}
            />

            {/* Add Member Modal */}
            {modalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div style={{ ...styles.card, width: '100%', maxWidth: '500px' }}>
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold">注册新成员</h3>
                            <button onClick={() => setModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                                <X size={24} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">姓名</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="输入姓名"
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">学号</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="输入学号"
                                    value={newStudentId}
                                    onChange={(e) => setNewStudentId(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">班级</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="例如：2023级 计算机一班"
                                    value={newClass}
                                    onChange={(e) => setNewClass(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">身份</label>
                                <div style={{ position: 'relative' }}>
                                    <div
                                        className="input-field"
                                        style={{
                                            backgroundColor: 'var(--bg-hover)',
                                            borderColor: 'var(--border-color)',
                                            color: 'var(--text-primary)',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between'
                                        }}
                                        onClick={() => setRoleDropdownOpen(!roleDropdownOpen)}
                                    >
                                        <span>{(roleOptions.find(r => r.value === newMemberRole) || roleOptions[0]).label}</span>
                                        <ChevronDown size={18} style={{ color: 'var(--text-secondary)' }} />
                                    </div>

                                    {roleDropdownOpen && (
                                        <div style={{
                                            position: 'absolute',
                                            top: '100%',
                                            left: 0,
                                            right: 0,
                                            marginTop: '0.5rem',
                                            backgroundColor: 'var(--bg-card)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '0.5rem',
                                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                                            zIndex: 50,
                                            overflow: 'hidden'
                                        }}>
                                            {roleOptions.map(option => (
                                                <div
                                                    key={option.value}
                                                    onClick={() => {
                                                        setNewMemberRole(option.value);
                                                        setRoleDropdownOpen(false);
                                                    }}
                                                    style={{
                                                        padding: '0.75rem 1rem',
                                                        cursor: 'pointer',
                                                        color: 'var(--text-primary)',
                                                        backgroundColor: newMemberRole === option.value ? 'var(--bg-hover)' : 'transparent',
                                                        transition: 'background-color 0.15s ease'
                                                    }}
                                                    onMouseOver={(e) => {
                                                        if (newMemberRole !== option.value) e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                                                    }}
                                                    onMouseOut={(e) => {
                                                        if (newMemberRole !== option.value) e.currentTarget.style.backgroundColor = 'transparent';
                                                    }}
                                                >
                                                    {option.label}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-card)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    marginRight: '0.75rem',
                                    transition: 'background-color 0.2s'
                                }}
                                onMouseOver={(e) => e.target.style.backgroundColor = 'var(--bg-hover)'}
                                onMouseOut={(e) => e.target.style.backgroundColor = 'var(--bg-card)'}
                                onClick={() => setModalOpen(false)}
                            >
                                取消
                            </button>
                            <button
                                className="btn-primary"
                                style={{ width: 'auto' }}
                                onClick={handleCreate}
                            >
                                确认注册
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Member Modal */}
            {editModalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div style={{ ...styles.card, width: '100%', maxWidth: '500px' }}>
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold">编辑成员信息</h3>
                            <button onClick={() => setEditModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                                <X size={24} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">姓名</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="输入姓名"
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">学号</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="输入学号"
                                    value={newStudentId}
                                    onChange={(e) => setNewStudentId(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">班级</label>
                                <input
                                    type="text"
                                    className="input-field"
                                    placeholder="例如：2023级 计算机一班"
                                    value={newClass}
                                    onChange={(e) => setNewClass(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">身份</label>
                                <div style={{ position: 'relative' }}>
                                    <div
                                        className="input-field"
                                        style={{
                                            backgroundColor: 'var(--bg-hover)',
                                            borderColor: 'var(--border-color)',
                                            color: 'var(--text-primary)',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between'
                                        }}
                                        onClick={() => setRoleDropdownOpen(!roleDropdownOpen)}
                                    >
                                        <span>{(roleOptions.find(r => r.value === newMemberRole) || roleOptions[0]).label}</span>
                                        <ChevronDown size={18} style={{ color: 'var(--text-secondary)' }} />
                                    </div>

                                    {roleDropdownOpen && (
                                        <div style={{
                                            position: 'absolute',
                                            top: '100%',
                                            left: 0,
                                            right: 0,
                                            marginTop: '0.5rem',
                                            backgroundColor: 'var(--bg-card)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '0.5rem',
                                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                                            zIndex: 50,
                                            overflow: 'hidden'
                                        }}>
                                            {roleOptions.map(option => (
                                                <div
                                                    key={option.value}
                                                    onClick={() => {
                                                        setNewMemberRole(option.value);
                                                        setRoleDropdownOpen(false);
                                                    }}
                                                    style={{
                                                        padding: '0.75rem 1rem',
                                                        cursor: 'pointer',
                                                        color: 'var(--text-primary)',
                                                        backgroundColor: newMemberRole === option.value ? 'var(--bg-hover)' : 'transparent',
                                                        transition: 'background-color 0.15s ease'
                                                    }}
                                                    onMouseOver={(e) => {
                                                        if (newMemberRole !== option.value) e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                                                    }}
                                                    onMouseOut={(e) => {
                                                        if (newMemberRole !== option.value) e.currentTarget.style.backgroundColor = 'transparent';
                                                    }}
                                                >
                                                    {option.label}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-card)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    marginRight: '0.75rem',
                                    transition: 'background-color 0.2s'
                                }}
                                onMouseOver={(e) => e.target.style.backgroundColor = 'var(--bg-hover)'}
                                onMouseOut={(e) => e.target.style.backgroundColor = 'var(--bg-card)'}
                                onClick={() => setEditModalOpen(false)}
                            >
                                取消
                            </button>
                            <button
                                className="btn-primary"
                                style={{ width: 'auto' }}
                                onClick={handleUpdate}
                            >
                                保存修改
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MemberManagementView;
