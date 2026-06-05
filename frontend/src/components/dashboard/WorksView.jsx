import React, { useState, useEffect } from 'react';
import ApiService from '../../services/api';
import { Upload, CheckCircle, XCircle, Image, Clock, FileText, ChevronRight, ChevronDown } from 'lucide-react';

const WorksView = () => {
    const [stats, setStats] = useState({
        total: 0,
        success: 0,
        failed: 0
    });

    const [submissions, setSubmissions] = useState([]);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadTitle, setUploadTitle] = useState('');
    const [uploadDescription, setUploadDescription] = useState('');
    const [isClosing, setIsClosing] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    const handleClose = () => {
        setIsClosing(true);
        setTimeout(() => {
            setUploadOpen(false);
            setIsClosing(false);
            setIsDragging(false);
        }, 200);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            setUploadFile(files[0]);
        }
    };

    const fetchData = async () => {
        try {
            const [statsData, worksData] = await Promise.all([
                ApiService.works.getStats(),
                ApiService.works.list()
            ]);
            setStats(statsData);
            setSubmissions(worksData.works);
        } catch (err) {
            console.error('Failed to fetch works data:', err);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleUpload = async () => {
        if (!uploadFile) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', uploadFile);
        if (uploadTitle) {
            formData.append('title', uploadTitle);
        }
        if (uploadDescription) {
            formData.append('description', uploadDescription);
        }

        try {
            await ApiService.works.upload(formData);
            setUploadOpen(false);
            setUploadFile(null);
            setUploadTitle('');
            setUploadDescription('');
            fetchData(); // Refresh data
            alert('上传成功！');
        } catch (err) {
            alert(err.error || '上传失败');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDownload = async (work) => {
        try {
            console.log('Starting download for work:', work);
            const blob = await ApiService.works.download(work.id);
            console.log('Successfully received blob from API:', blob);

            if (!blob || blob.size === 0) {
                throw new Error('Received empty or invalid file data');
            }

            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;

            // Use the original filename stored in the database
            const downloadName = work.originalName || work.fileName || `work_${work.id}`;
            console.log('Setting download attribute to:', downloadName);
            link.setAttribute('download', downloadName);

            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
            window.URL.revokeObjectURL(url);
            console.log('Download triggered successfully');
        } catch (err) {
            console.error('Download execution failed:', err);
            // Attempt to extract error message from blob if possible
            if (err instanceof Blob) {
                const reader = new FileReader();
                reader.onload = () => {
                    try {
                        const json = JSON.parse(reader.result);
                        alert(`下载失败: ${json.error || '服务器错误'}`);
                    } catch (e) {
                        alert('文件下载失败，请联系管理员');
                    }
                };
                reader.readAsText(err);
            } else {
                alert(`下载失败: ${err.message || '网络连接错误'}`);
            }
        }
    };

    const [selectedWork, setSelectedWork] = useState(null);
    const [detailsOpen, setDetailsOpen] = useState(false);

    // Inline Styles using CSS variables
    const styles = {
        container: {
            animation: 'fadeIn 0.5s ease',
            color: 'var(--text-primary)'
        },
        header: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.5rem'
        },
        grid: {
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1.5rem',
            marginBottom: '2rem'
        },
        card: {
            backgroundColor: 'var(--bg-card)',
            borderRadius: '1rem',
            padding: '1.5rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem'
        },
        iconBox: {
            width: '3.5rem',
            height: '3.5rem',
            borderRadius: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        },
        listCard: {
            backgroundColor: 'var(--bg-card)',
            borderRadius: '1rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
            overflow: 'hidden'
        },
        listHeader: {
            padding: '1.5rem',
            borderBottom: '1px solid var(--border-color)',
            fontWeight: 'bold',
            fontSize: '1.125rem',
            color: 'var(--text-primary)'
        },
        listItem: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--border-color)',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
            color: 'var(--text-primary)'
        },
        statusBadge: (status) => ({
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            padding: '0.25rem 0.75rem',
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: 500,
            backgroundColor: status === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            color: status === 'success' ? '#10b981' : '#ef4444'
        }),
        modalOverlay: {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            backdropFilter: 'blur(4px)',
            animation: 'fadeIn 0.3s ease'
        },
        modalCard: {
            backgroundColor: 'var(--bg-card)',
            width: '100%',
            maxWidth: '500px',
            borderRadius: '1.5rem',
            padding: '2rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            position: 'relative'
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h2 className="text-2xl font-bold">作品管理</h2>
                <button
                    className="btn-primary"
                    style={{ width: 'auto' }}
                    onClick={() => setUploadOpen(true)}
                >
                    <Upload size={18} />
                    <span style={{ marginLeft: '0.5rem' }}>上传作品</span>
                </button>
            </div>

            {/* 3 Stats Blocks */}
            <div style={styles.grid}>
                {/* Total */}
                <div style={styles.card}>
                    <div style={{ ...styles.iconBox, backgroundColor: 'rgba(99, 102, 241, 0.1)', color: '#6366f1' }}>
                        <Image size={28} />
                    </div>
                    <div>
                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>总提交作品</p>
                        <p style={{ fontSize: '1.875rem', fontWeight: 'bold', color: 'var(--text-primary)', lineHeight: 1.2 }}>{stats.total}</p>
                    </div>
                </div>

                {/* Success */}
                <div style={styles.card}>
                    <div style={{ ...styles.iconBox, backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
                        <CheckCircle size={28} />
                    </div>
                    <div>
                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>提交成功</p>
                        <p style={{ fontSize: '1.875rem', fontWeight: 'bold', color: 'var(--text-primary)', lineHeight: 1.2 }}>{stats.success}</p>
                    </div>
                </div>

                {/* Failed */}
                <div style={styles.card}>
                    <div style={{ ...styles.iconBox, backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
                        <XCircle size={28} />
                    </div>
                    <div>
                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>提交失败</p>
                        <p style={{ fontSize: '1.875rem', fontWeight: 'bold', color: 'var(--text-primary)', lineHeight: 1.2 }}>{stats.failed}</p>
                    </div>
                </div>
            </div>

            {/* Submission Records List */}
            <div style={styles.listCard}>
                <div style={styles.listHeader}>
                    提交记录
                </div>
                <div>
                    {/* List Header Row */}
                    <div style={{ display: 'flex', padding: '0.75rem 1.5rem', backgroundColor: 'var(--bg-hover)', fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        <div style={{ width: '40%' }}>作品名称</div>
                        <div style={{ width: '30%' }}>提交时间</div>
                        <div style={{ width: '30%' }}>状态</div>
                    </div>

                    {submissions.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                            暂无提交记录
                        </div>
                    ) : (
                        submissions.map((item) => (
                            <div
                                key={item.id}
                                style={styles.listItem}
                                className="hover:bg-gray-50/5 group"
                                onClick={() => {
                                    setSelectedWork(item);
                                    setDetailsOpen(true);
                                }}
                            >
                                <div style={{ width: '40%', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <FileText size={16} style={{ color: 'var(--text-secondary)' }} />
                                    <span className="truncate">{item.title}</span>
                                </div>
                                <div style={{ width: '25%', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                    {item.date}
                                </div>
                                <div style={{ width: '20%' }}>
                                    <span style={styles.statusBadge(item.status)}>
                                        {item.status === 'success' ? '通过' : '未通过'}
                                    </span>
                                </div>
                                <div style={{ width: '15%', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDownload(item);
                                        }}
                                        className="p-1.5 hover:bg-gray-100/10 rounded-lg transition-colors text-indigo-400 opacity-0 group-hover:opacity-100"
                                        title="下载作品"
                                    >
                                        <Upload size={16} style={{ transform: 'rotate(180deg)' }} />
                                    </button>
                                    <ChevronRight size={16} style={{ color: 'var(--glass-border)' }} />
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Details Modal */}
            {detailsOpen && selectedWork && (
                <div style={styles.modalOverlay} onClick={() => setDetailsOpen(false)}>
                    <div style={styles.modalCard} onClick={e => e.stopPropagation()}>

                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-500">
                                <FileText size={32} />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold">{selectedWork.title}</h3>
                                <p className="text-sm text-gray-400 truncate max-w-[300px]">{selectedWork.originalName || selectedWork.fileName}</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">作品简介</label>
                                <div className="mt-1 p-4 bg-gray-50/5 rounded-xl border border-gray-100/10 text-gray-300 leading-relaxed max-h-[200px] overflow-y-auto">
                                    {selectedWork.description || '暂无详细描述'}
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">提交日期</label>
                                    <p className="mt-1 font-medium">{selectedWork.date}</p>
                                </div>
                                <div className="flex-1">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">审核状态</label>
                                    <div className="mt-1">
                                        <span style={styles.statusBadge(selectedWork.status)}>
                                            {selectedWork.status === 'success' ? '通过' : '未通过'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button
                            className="btn-primary w-full mt-8"
                            onClick={() => handleDownload(selectedWork)}
                        >
                            下载该作品资源
                        </button>
                    </div>
                </div>
            )}

            {/* Upload Modal (Fixed Centered Modal) */}
            {uploadOpen && (
                <div
                    className={`fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-md ${isClosing ? 'animate-fade-out' : 'animate-fade-in'}`}
                    onClick={handleClose}
                >
                    <div
                        className={`bg-white w-full max-w-lg shadow-2xl relative overflow-hidden ${isClosing ? 'animate-modal-out' : 'animate-modal'}`}
                        style={{
                            backgroundColor: 'var(--bg-card)',
                            color: 'var(--text-primary)',
                            borderRadius: '1.75rem', // Super modern rounded corners
                            border: '1px solid var(--border-color)'
                        }}
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header Section */}
                        <div className="px-8 pt-8 pb-4 flex justify-between items-start">
                            <div>
                                <h3 className="text-2xl font-black tracking-tight flex items-center gap-2.5">
                                    <div className="p-2.5 bg-indigo-600 rounded-xl text-white shadow-lg shadow-indigo-200">
                                        <Upload size={20} strokeWidth={3} />
                                    </div>
                                    <span style={{ background: 'linear-gradient(to right, #6366f1, #ec4899)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                        上传作品
                                    </span>
                                </h3>
                                <p className="text-xs text-gray-400 font-medium mt-1.5 ml-1 tracking-wide">SHOW YOUR CREATIVITY</p>
                            </div>
                            <button
                                onClick={handleClose}
                                className="transition-all text-gray-400 hover:text-indigo-500 hover:rotate-90 hover:bg-indigo-50 rounded-full"
                                style={{ background: 'none', border: 'none', padding: '0.5rem', cursor: 'pointer', outline: 'none' }}
                            >
                                <ChevronDown size={28} />
                            </button>
                        </div>

                        {/* Body Section */}
                        <div className="px-8 py-4 space-y-6">
                            <div className="group">
                                <label className="block text-xs font-bold uppercase tracking-wider mb-2 text-indigo-400 group-focus-within:text-indigo-600 transition-colors">
                                    作品标题
                                </label>
                                <input
                                    type="text"
                                    className="w-full transition-all"
                                    placeholder="给你的作品起个好听的名字..."
                                    value={uploadTitle}
                                    onChange={(e) => setUploadTitle(e.target.value)}
                                    style={{
                                        backgroundColor: 'var(--bg-hover)',
                                        border: '2px solid transparent',
                                        borderRadius: '1rem',
                                        padding: '1rem 1.25rem',
                                        fontSize: '0.95rem',
                                        color: 'var(--text-primary)',
                                        outline: 'none'
                                    }}
                                    onFocus={(e) => e.target.style.borderColor = 'var(--primary-color)'}
                                    onBlur={(e) => e.target.style.borderColor = 'transparent'}
                                />
                            </div>

                            <div className="group">
                                <label className="block text-xs font-bold uppercase tracking-wider mb-2 text-gray-400 group-focus-within:text-indigo-500 transition-colors">
                                    创意描述
                                </label>
                                <textarea
                                    className="w-full transition-all"
                                    placeholder="描述一下你的技术栈、设计思路或者是灵感来源..."
                                    value={uploadDescription}
                                    onChange={(e) => setUploadDescription(e.target.value)}
                                    style={{
                                        backgroundColor: 'var(--bg-hover)',
                                        border: '2px solid transparent',
                                        borderRadius: '1rem',
                                        padding: '1rem 1.25rem',
                                        fontSize: '0.9rem',
                                        color: 'var(--text-primary)',
                                        height: '110px', // Slightly taller
                                        resize: 'none',
                                        outline: 'none',
                                        lineHeight: '1.6'
                                    }}
                                    onFocus={(e) => e.target.style.borderColor = 'var(--primary-color)'}
                                    onBlur={(e) => e.target.style.borderColor = 'transparent'}
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider mb-2 text-gray-400">
                                    核心文件
                                </label>
                                <div
                                    style={{
                                        border: isDragging ? '2px dashed var(--primary-color)' : '2px dashed var(--border-color)',
                                        borderRadius: '1.25rem',
                                        padding: '1.5rem',
                                        textAlign: 'center',
                                        cursor: 'pointer',
                                        backgroundColor: isDragging ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-card)',
                                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                        transform: isDragging ? 'scale(1.02)' : 'scale(1)'
                                    }}
                                    className="hover:border-indigo-400 hover:bg-indigo-50/30 group relative overflow-hidden"
                                    onClick={() => document.getElementById('file-upload').click()}
                                    onDragOver={handleDragOver}
                                    onDragLeave={handleDragLeave}
                                    onDrop={handleDrop}
                                >
                                    <input
                                        type="file"
                                        id="file-upload"
                                        className="hidden"
                                        onChange={(e) => setUploadFile(e.target.files[0])}
                                    />

                                    <div className="relative z-10 flex flex-col items-center justify-center gap-3">
                                        <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center group-hover:scale-110 group-hover:bg-indigo-100 transition-all duration-300">
                                            {uploadFile ?
                                                <CheckCircle size={28} className="text-green-500" /> :
                                                <Upload size={24} className="text-gray-400 group-hover:text-indigo-500" />
                                            }
                                        </div>
                                        {uploadFile ? (
                                            <div className="animate-fade-in">
                                                <p className="text-indigo-600 font-bold text-sm truncate max-w-[200px]">{uploadFile.name}</p>
                                                <p className="text-[10px] text-gray-400">点击更换</p>
                                            </div>
                                        ) : (
                                            <div className="text-gray-400">
                                                <p className="text-sm font-medium group-hover:text-indigo-500 transition-colors">
                                                    {isDragging ? '松开手指即可上传' : '点击或拖拽文件到这里'}
                                                </p>
                                                <p className="text-[10px] mt-0.5 opacity-70">支持任意格式</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="px-8 pb-8 pt-2 flex gap-4 mt-4">
                            <button
                                style={{
                                    flex: 1,
                                    padding: '1rem',
                                    borderRadius: '1rem',
                                    color: 'var(--text-secondary)',
                                    fontWeight: 700,
                                    fontSize: '0.9rem',
                                    background: 'transparent',
                                    transition: 'all 0.2s'
                                }}
                                className="hover:bg-gray-100 opacity-60 hover:opacity-100"
                                onClick={handleClose}
                                disabled={isUploading}
                            >
                                取消
                            </button>
                            <button
                                className="btn-primary shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50"
                                style={{
                                    flex: 2,
                                    padding: '1rem',
                                    borderRadius: '1rem',
                                    fontSize: '0.95rem',
                                    fontWeight: 800,
                                    letterSpacing: '0.025em'
                                }}
                                onClick={handleUpload}
                                disabled={!uploadFile || isUploading}
                            >
                                {isUploading ? (
                                    <span className="flex items-center gap-2">
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin"></div>
                                        UPLOADING...
                                    </span>
                                ) : '立即上传'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default WorksView;
