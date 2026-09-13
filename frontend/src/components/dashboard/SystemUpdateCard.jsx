import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    RefreshCw, Download, GitBranch, AlertTriangle, CheckCircle2,
    Power, ChevronDown, ChevronUp, PlayCircle, ListTree, Loader2, Database, ShieldCheck
} from 'lucide-react';
import ApiService from '../../services/api';

const STATE_LABELS = {
    idle: '尚未检查',
    checking: '正在检查',
    up_to_date: '已是最新',
    update_available: '有可用更新',
    blocked: '需要人工处理',
    downloading: '正在下载',
    installing: '正在安装',
    installed: '更新完成（待重启）',
    error: '出错',
};

const STATE_COLORS = {
    up_to_date: '#16a34a',
    installed: '#16a34a',
    update_available: '#2563eb',
    blocked: '#d97706',
    error: '#dc2626',
    checking: '#7c3aed',
    downloading: '#7c3aed',
    installing: '#7c3aed',
};

const SOURCE_LABELS = {
    git: 'git 仓库拉取',
    release: 'GitHub Release 包',
};

const card = {
    backgroundColor: 'var(--bg-card)',
    borderRadius: '1rem',
    padding: '1.5rem',
    border: '1px solid var(--border-color)',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
    marginBottom: '1.5rem',
    maxWidth: '600px',
    color: 'var(--text-primary)',
};

const title = {
    fontSize: '1.125rem',
    fontWeight: 600,
    marginBottom: '1rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    color: 'var(--text-primary)',
};

const row = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.35rem 0',
    fontSize: '0.875rem',
    gap: '1rem',
};

const label = { color: 'var(--text-secondary)' };

const btn = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    padding: '0.5rem 0.9rem',
    borderRadius: '0.5rem',
    backgroundColor: 'var(--bg-hover)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-color)',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '0.8125rem',
};

const btnPrimary = Object.assign({}, btn, {
    backgroundColor: 'var(--primary-color, #4f46e5)',
    color: '#fff',
    border: '1px solid transparent',
});

const box = {
    marginTop: '0.75rem',
    padding: '0.75rem',
    borderRadius: '0.5rem',
    backgroundColor: 'var(--bg-hover)',
    border: '1px solid var(--border-color)',
    fontSize: '0.8125rem',
};

const mono = {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    fontSize: '0.75rem',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    margin: 0,
};

function Pill(state) {
    return {
        display: 'inline-block',
        padding: '0.15rem 0.6rem',
        borderRadius: '999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: '#fff',
        backgroundColor: STATE_COLORS[state] || '#6b7280',
    };
}

const SystemUpdateCard = () => {
    const [status, setStatus] = useState(null);
    const [error, setError] = useState('');
    const [preview, setPreview] = useState(null);
    const [showLogs, setShowLogs] = useState(false);
    const [showNotes, setShowNotes] = useState(false);
    const pollRef = useRef(null);

    const refresh = useCallback(async () => {
        try {
            const data = await ApiService.update.status();
            setStatus(data);
            setError('');
            return data;
        } catch (err) {
            setError((err && err.error) || '无法获取更新状态（需要老师或社长权限）');
            return null;
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    useEffect(() => {
        if (status && status.busy) {
            pollRef.current = setInterval(refresh, 1500);
            return () => clearInterval(pollRef.current);
        }
        return undefined;
    }, [status, refresh]);

    const runAction = async (fn, confirmText) => {
        if (confirmText && !window.confirm(confirmText)) {
            return;
        }
        setError('');
        setPreview(null);
        try {
            const res = await fn();
            if (res && res.accepted === false && res.reason) {
                setError(res.reason);
            }
            if (res && res.status) {
                setStatus(res.status);
            } else {
                await refresh();
            }
        } catch (err) {
            setError((err && err.error) || '操作失败');
        }
    };

    const handlePreview = async () => {
        setError('');
        try {
            setPreview(await ApiService.update.preview());
        } catch (err) {
            setError((err && err.error) || '预览失败');
        }
    };

    if (error && !status) {
        return (
            <div style={card}>
                <h3 style={title}>
                    <RefreshCw size={20} style={{ color: 'var(--primary-color)' }} />
                    系统更新
                </h3>
                <p style={{ color: '#dc2626', fontSize: '0.875rem' }}>{error}</p>
            </div>
        );
    }

    if (!status) {
        return (
            <div style={card}>
                <h3 style={title}>
                    <RefreshCw size={20} style={{ color: 'var(--primary-color)' }} />
                    系统更新
                </h3>
                <p style={{ ...label, fontSize: '0.875rem' }}>正在读取更新状态…</p>
            </div>
        );
    }

    const info = status.update || {};
    const details = info.details || {};
    const isGit = info.source === 'git';
    const canInstall = status.state === 'update_available' && !info.blocked && !status.busy;
    const report = status.report;

    return (
        <div style={card}>
            <h3 style={title}>
                <RefreshCw size={20} style={{ color: 'var(--primary-color)' }} />
                系统更新
            </h3>

            <div style={row}>
                <span style={label}>当前版本</span>
                <span style={{ fontWeight: 600 }}>{status.current_version || info.current_version || '未知'}</span>
            </div>
            <div style={row}>
                <span style={label}>远端版本</span>
                <span style={{ fontWeight: 600 }}>{status.remote_version || info.remote_version || '—'}</span>
            </div>
            <div style={row}>
                <span style={label}>状态</span>
                <span style={Pill(status.state)}>{STATE_LABELS[status.state] || status.state}</span>
            </div>
            <div style={row}>
                <span style={label}>更新来源</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    {isGit ? <GitBranch size={14} /> : <Download size={14} />}
                    {SOURCE_LABELS[info.source] || '未确定'}
                </span>
            </div>
            {details.commits_behind ? (
                <div style={row}>
                    <span style={label}>落后提交</span>
                    <span>{details.commits_behind} 个</span>
                </div>
            ) : null}
            <div style={row}>
                <span style={label}>上次检查</span>
                <span>{status.last_check_at ? status.last_check_at.replace('T', ' ') : '尚未检查'}</span>
            </div>

            <p style={{ marginTop: '0.75rem', fontSize: '0.875rem' }}>{status.message}</p>

            {status.data && status.data.enabled ? (
                <div style={{ ...box, borderColor: '#0ea5e9', backgroundColor: 'rgba(14, 165, 233, 0.07)' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 600, color: '#0369a1' }}>
                        <ShieldCheck size={16} />
                        <span>受保护的用户数据（更新时永不覆盖）</span>
                    </div>
                    <div style={{ ...row, padding: '0.2rem 0' }}>
                        <span style={label}>保护路径</span>
                        <span style={mono}>{(status.data.protected_paths || []).join('、')}</span>
                    </div>
                    <div style={{ ...row, padding: '0.2rem 0' }}>
                        <span style={label}>数据文件</span>
                        <span>{status.data.file_count} 个，共 {status.data.total_mb} MB</span>
                    </div>
                    {status.data.database_files && status.data.database_files.length ? (
                        <div style={{ ...row, padding: '0.2rem 0' }}>
                            <span style={label}><Database size={13} /> 数据库</span>
                            <span style={mono}>{status.data.database_files.join('、')}</span>
                        </div>
                    ) : null}
                </div>
            ) : null}

            {status.busy ? (
                <div style={{ marginTop: '0.5rem' }}>
                    <div style={{ height: '6px', borderRadius: '999px', backgroundColor: 'var(--bg-hover)', overflow: 'hidden' }}>
                        <div style={{
                            height: '100%',
                            width: (status.progress || 0) + '%',
                            backgroundColor: 'var(--primary-color, #4f46e5)',
                            transition: 'width 0.3s',
                        }} />
                    </div>
                </div>
            ) : null}

            {info.blocked ? (
                <div style={{ ...box, borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.08)' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', color: '#b45309', fontWeight: 600 }}>
                        <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <span>为保护你的本地改动，更新已被阻止</span>
                    </div>
                    <p style={{ margin: '0.4rem 0 0', color: 'var(--text-secondary)' }}>{info.blocked_reason}</p>
                    {details.dirty_files && details.dirty_files.length ? (
                        <details style={{ marginTop: '0.4rem' }}>
                            <summary style={{ cursor: 'pointer' }}>
                                查看未提交的文件（{details.dirty_files.length}）
                            </summary>
                            <pre style={{ ...mono, marginTop: '0.4rem', maxHeight: '180px', overflow: 'auto' }}>
                                {details.dirty_files.join('\n')}
                            </pre>
                        </details>
                    ) : null}
                </div>
            ) : null}

            {status.restart_required ? (
                <div style={{ ...box, borderColor: '#16a34a', backgroundColor: 'rgba(22, 163, 74, 0.08)' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: '#15803d', fontWeight: 600 }}>
                        <CheckCircle2 size={16} />
                        <span>更新已写入磁盘，需要重启后端服务才会生效</span>
                    </div>
                </div>
            ) : null}

            {info.notes ? (
                <div style={box}>
                    <div
                        onClick={() => setShowNotes(!showNotes)}
                        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
                    >
                        {showNotes ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        更新说明
                    </div>
                    {showNotes ? (
                        <pre style={{ ...mono, marginTop: '0.5rem', maxHeight: '220px', overflow: 'auto' }}>
                            {info.notes}
                        </pre>
                    ) : null}
                </div>
            ) : null}

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
                <button
                    style={btn}
                    disabled={status.busy}
                    onClick={() => runAction(() => ApiService.update.check({ source: 'auto' }))}
                >
                    {status.busy ? <Loader2 size={15} /> : <RefreshCw size={15} />}
                    检查更新
                </button>

                <button style={btn} disabled={!info.available || status.busy} onClick={handlePreview}>
                    <ListTree size={15} />
                    预览变更
                </button>

                <button
                    style={btn}
                    disabled={!canInstall}
                    onClick={() => runAction(
                        () => ApiService.update.install({ dry_run: true }),
                        '预演安装会完整走一遍流程，但不会修改任何文件。继续？'
                    )}
                >
                    <PlayCircle size={15} />
                    预演
                </button>

                <button
                    style={canInstall ? btnPrimary : btn}
                    disabled={!canInstall}
                    onClick={() => runAction(
                        () => ApiService.update.install({ dry_run: false }),
                        '即将把更新写入项目文件。数据库、上传文件与配置会被保留，写入前会自动备份。确认继续？'
                    )}
                >
                    <Download size={15} />
                    立即更新
                </button>

                {status.config && status.config.allow_restart ? (
                    <button
                        style={btn}
                        disabled={status.busy}
                        onClick={() => runAction(
                            () => ApiService.update.restart(),
                            '将重启后端进程，期间服务会短暂中断。确认继续？'
                        )}
                    >
                        <Power size={15} />
                        重启后端
                    </button>
                ) : null}
            </div>

            {preview ? (
                <div style={box}>
                    <strong>变更预览</strong>
                    <p style={{ margin: '0.35rem 0 0', color: 'var(--text-secondary)' }}>{preview.message}</p>
                    {preview.files && preview.files.length ? (
                        <pre style={{ ...mono, marginTop: '0.4rem', maxHeight: '220px', overflow: 'auto' }}>
                            {preview.files.join('\n')}
                        </pre>
                    ) : null}
                </div>
            ) : null}

            {report ? (
                <div style={box}>
                    <strong>{report.dry_run ? '预演结果（未写入任何文件）' : '安装结果'}</strong>
                    <div style={{ ...row, padding: '0.2rem 0' }}>
                        <span style={label}>写入文件</span><span>{report.written_count}</span>
                    </div>
                    <div style={{ ...row, padding: '0.2rem 0' }}>
                        <span style={label}>内容未变</span><span>{report.unchanged_count}</span>
                    </div>
                    <div style={{ ...row, padding: '0.2rem 0' }}>
                        <span style={label}>受保护保留</span><span>{report.preserved_count}</span>
                    </div>
                    <div style={{ ...row, padding: '0.2rem 0' }}>
                        <span style={label}>跳过</span><span>{report.skipped_count}</span>
                    </div>
                    {report.backup_dir ? (
                        <div style={{ ...row, padding: '0.2rem 0' }}>
                            <span style={label}>备份目录</span>
                            <span style={{ ...mono }}>{report.backup_dir}</span>
                        </div>
                    ) : null}
                    {report.rolled_back ? (
                        <p style={{ color: '#b45309', margin: '0.4rem 0 0' }}>安装失败，已自动回滚到更新前状态。</p>
                    ) : null}
                    {report.data && report.data.enabled ? (
                        <div style={{ marginTop: '0.4rem' }}>
                            <div style={{ color: '#0369a1' }}>
                                用户数据：{report.data.protected_files} 个文件受保护
                                {report.data.merge_touched && report.data.merge_touched.length
                                    ? '，其中 ' + report.data.merge_touched.length + ' 个被本次更新波及，已还原为本地版本'
                                    : '，本次更新未触及'}
                            </div>
                            {report.data.merge_touched && report.data.merge_touched.length ? (
                                <pre style={{ ...mono, maxHeight: '140px', overflow: 'auto' }}>
                                    {report.data.merge_touched.join('\n')}
                                </pre>
                            ) : null}
                            {report.data.problems && report.data.problems.length ? (
                                <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.1rem', color: '#dc2626' }}>
                                    {report.data.problems.map((p, i) => <li key={i}>{p}</li>)}
                                </ul>
                            ) : null}
                        </div>
                    ) : null}
                    {report.notes && report.notes.length ? (
                        <ul style={{ margin: '0.4rem 0 0', paddingLeft: '1.1rem' }}>
                            {report.notes.map((note, i) => <li key={i}>{note}</li>)}
                        </ul>
                    ) : null}
                    {report.errors && report.errors.length ? (
                        <ul style={{ margin: '0.4rem 0 0', paddingLeft: '1.1rem', color: '#dc2626' }}>
                            {report.errors.map((err, i) => <li key={i}>{err}</li>)}
                        </ul>
                    ) : null}
                </div>
            ) : null}

            {error && status ? (
                <p style={{ color: '#dc2626', fontSize: '0.8125rem', marginTop: '0.6rem' }}>{error}</p>
            ) : null}

            {status.source_notes && status.source_notes.length ? (
                <div style={box}>
                    {status.source_notes.map((note, i) => (
                        <div key={i} style={{ color: 'var(--text-secondary)' }}>{note}</div>
                    ))}
                </div>
            ) : null}

            <div
                onClick={() => setShowLogs(!showLogs)}
                style={{ marginTop: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8125rem', ...label }}
            >
                {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                后台日志
            </div>
            {showLogs ? (
                <pre style={{ ...mono, marginTop: '0.4rem', maxHeight: '240px', overflow: 'auto', ...box }}>
                    {(status.logs || []).join('\n') || '（暂无日志）'}
                </pre>
            ) : null}
        </div>
    );
};

export default SystemUpdateCard;
