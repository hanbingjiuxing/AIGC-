import React, { useState, useEffect } from 'react';
import ApiService from '../../services/api';
import { X, Image, FileText, ExternalLink, Calendar, CheckCircle, XCircle } from 'lucide-react';

const MemberWorksModal = ({ isOpen, onClose, member }) => {
    if (!isOpen || !member) return null;

    const [works, setWorks] = useState([]);

    useEffect(() => {
        if (member && isOpen) {
            console.log('Fetching works for member:', member);
            const fetchWorks = async () => {
                try {
                    const data = await ApiService.works.list({ user_id: member.id });
                    console.log('Works fetched:', data);
                    setWorks(data.works || []);
                } catch (err) {
                    console.error('Failed to fetch user works:', err);
                    setWorks([]);
                }
            };
            fetchWorks();
        } else {
            setWorks([]);
        }
    }, [member, isOpen]);

    const handleDownload = async (work) => {
        try {
            console.log('MemberWorksModal: Starting download for work:', work);
            const blob = await ApiService.works.download(work.id);
            console.log('MemberWorksModal: Successfully received blob:', blob);

            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;

            // Use the original filename stored in the database
            const downloadName = work.originalName || work.fileName || `work_${work.id}`;
            console.log('MemberWorksModal: Setting download attribute to:', downloadName);
            link.setAttribute('download', downloadName);

            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
            window.URL.revokeObjectURL(url);
            console.log('MemberWorksModal: Download triggered successfully');
        } catch (err) {
            console.error('Download execution failed:', err);
            alert('文件下载失败');
        }
    };

    const styles = {
        overlay: {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 50,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem'
        },
        card: {
            backgroundColor: 'var(--bg-card)',
            width: '100%',
            maxWidth: '800px',
            borderRadius: '1rem',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            overflow: 'hidden',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            animation: 'fadeIn 0.3s ease-out'
        },
        header: {
            padding: '1.5rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: 'var(--bg-card)'
        },
        body: {
            padding: '1.5rem',
            maxHeight: '70vh',
            overflowY: 'auto'
        },
        grid: {
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
            gap: '1.5rem'
        },
        workCard: {
            border: '1px solid var(--border-color)',
            borderRadius: '0.75rem',
            overflow: 'hidden',
            transition: 'all 0.2s',
            backgroundColor: 'var(--bg-hover)'
        },
        workPreview: {
            height: '140px',
            backgroundColor: 'var(--bg-card)', // fallback
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid var(--border-color)',
            color: 'var(--text-secondary)'
        },
        workInfo: {
            padding: '1rem'
        },
        badge: (status) => ({
            fontSize: '0.75rem',
            padding: '0.125rem 0.5rem',
            borderRadius: '9999px',
            backgroundColor: status === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            color: status === 'success' ? '#10b981' : '#ef4444',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.25rem'
        })
    };

    return (
        <div style={styles.overlay}>
            <div style={styles.card}>
                <div style={styles.header}>
                    <div>
                        <h3 className="text-xl font-bold">{member.name} 的作品集</h3>
                        <p className="text-sm text-gray-500 mt-1">共 {works.length} 个作品</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                        style={{ color: 'var(--text-secondary)' }}
                    >
                        <X size={24} />
                    </button>
                </div>

                <div style={styles.body}>
                    <div style={styles.grid}>
                        {works.length === 0 ? (
                            <div className="text-center py-8 text-gray-500 w-full col-span-full">
                                <p>暂无作品数据</p>
                            </div>
                        ) : (
                            works.map((work) => (
                                <div key={work.id} style={styles.workCard} className="hover:shadow-md">
                                    <div style={styles.workPreview}>
                                        {work.type === 'image' ? (
                                            <Image size={48} strokeWidth={1.5} />
                                        ) : (
                                            <FileText size={48} strokeWidth={1.5} />
                                        )}
                                    </div>
                                    <div style={styles.workInfo}>
                                        <h4 className="font-bold mb-1 truncate" title={work.title}>{work.title}</h4>
                                        <div className="bg-gray-50/5 rounded-lg p-2 mb-3 border border-gray-100/10">
                                            <p className="text-sm text-gray-300 leading-relaxed max-h-[80px] overflow-y-auto">
                                                {work.description || '暂无描述'}
                                            </p>
                                        </div>
                                        <div className="flex justify-between items-center mb-3">
                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                <Calendar size={12} />
                                                {work.date}
                                            </span>
                                            <span style={styles.badge(work.status)}>
                                                {work.status === 'success' ? <CheckCircle size={10} /> : <XCircle size={10} />}
                                                {work.status === 'success' ? '通过' : '驳回'}
                                            </span>
                                        </div>
                                        <button
                                            className="w-full py-2 rounded-md bg-white border border-gray-200 text-sm font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                                            style={{
                                                backgroundColor: 'var(--bg-card)',
                                                borderColor: 'var(--border-color)',
                                                color: 'var(--text-primary)'
                                            }}
                                            onClick={() => handleDownload(work)}
                                        >
                                            <ExternalLink size={14} />
                                            下载作品
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MemberWorksModal;
