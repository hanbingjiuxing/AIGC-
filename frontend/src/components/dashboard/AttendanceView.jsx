import React, { useState, useEffect } from 'react';
import ApiService from '../../services/api';
import { Calendar, CheckCircle, Clock, CalendarCheck, ChevronLeft, ChevronRight, BarChart2 } from 'lucide-react';

const AttendanceView = () => {
    const currentUser = JSON.parse(localStorage.getItem('user_info') || '{}');
    const isTeacher = currentUser.role === 'teacher';
    const isPresident = currentUser.role === 'president';
    const isStudent = currentUser.role === 'student' || currentUser.role === 'president';

    // Student State
    const [todaySigned, setTodaySigned] = useState(false);
    const [signHistory, setSignHistory] = useState([]);
    const [studentStatsData, setStudentStatsData] = useState({
        total: 0,
        rate: 0,
        totalDays: 0
    });

    // Teacher State
    const [semesterStart, setSemesterStart] = useState('');
    const [semesterEnd, setSemesterEnd] = useState('');
    const [teacherStats, setTeacherStats] = useState({
        students: [],
        totalStudents: 0,
        signedToday: 0,
        totalDays: 0
    });

    const fetchData = async () => {
        try {
            if (isStudent) {
                const [stats, history] = await Promise.all([
                    ApiService.attendance.getStats(),
                    ApiService.attendance.getHistory()
                ]);
                setStudentStatsData(stats);
                setTodaySigned(stats.todaySigned);
                setSignHistory(history.history);
            } else {
                const [stats, config] = await Promise.all([
                    ApiService.attendance.getStats(),
                    ApiService.attendance.getConfig()
                ]);
                setTeacherStats(stats);
                setSemesterStart(config.semesterStart);
                setSemesterEnd(config.semesterEnd);
            }
        } catch (err) {
            console.error('Failed to fetch attendance data:', err);
        }
    };

    useEffect(() => {
        fetchData();
    }, [isStudent]);

    const handleSignIn = async () => {
        try {
            await ApiService.attendance.signin();
            setTodaySigned(true);
            fetchData(); // Refresh data
            alert('签到成功！');
        } catch (err) {
            alert(err.error || '签到失败');
        }
    };

    const handleSaveConfig = async () => {
        try {
            await ApiService.attendance.setConfig({
                semesterStart,
                semesterEnd
            });
            alert('设置已保存');
            fetchData();
        } catch (err) {
            alert(err.error || '保存失败');
        }
    };

    const styles = {
        container: { animation: 'fadeIn 0.5s ease', color: 'var(--text-primary)' },
        card: {
            backgroundColor: 'var(--bg-card)',
            borderRadius: '1rem',
            padding: '1.5rem',
            border: '1px solid var(--border-color)',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
        },
        header: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.5rem'
        },
        signInBtn: {
            width: '100%',
            height: '200px',
            borderRadius: '1.5rem',
            border: 'none',
            background: todaySigned
                ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                : 'linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%)',
            color: 'white',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.5rem',
            fontWeight: 'bold',
            cursor: todaySigned ? 'default' : 'pointer',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            transition: 'transform 0.2s',
            opacity: todaySigned ? 0.9 : 1
        },
        historyItem: {
            display: 'flex',
            justifyContent: 'space-between',
            padding: '1rem',
            borderBottom: '1px solid var(--border-color)',
            alignItems: 'center'
        },
        statCard: {
            backgroundColor: 'var(--bg-hover)',
            padding: '1rem',
            borderRadius: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem'
        }
    };

    // Student/President Sign-in View
    if (isStudent) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>
                    <h2 className="text-2xl font-bold">每日签到</h2>
                    <p className="text-gray-500">保持良好的出勤记录</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <button
                            style={styles.signInBtn}
                            onClick={handleSignIn}
                            disabled={todaySigned}
                            className={!todaySigned ? 'hover:scale-105 active:scale-95' : ''}
                        >
                            {todaySigned ? (
                                <>
                                    <CheckCircle size={64} className="mb-4" />
                                    <span>今日已签到</span>
                                    <span className="text-sm font-normal mt-2 opacity-80">12:30:45</span>
                                </>
                            ) : (
                                <>
                                    <Clock size={64} className="mb-4" />
                                    <span>点击签到</span>
                                    <span className="text-sm font-normal mt-2 opacity-80">{new Date().toLocaleDateString()}</span>
                                </>
                            )}
                        </button>

                        <div style={{ ...styles.card, marginTop: '1.5rem' }}>
                            <h3 className="font-bold mb-4 flex items-center gap-2">
                                <BarChart2 size={20} className="text-indigo-500" />
                                本学期统计
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div style={styles.statCard}>
                                    <div className="text-2xl font-bold text-indigo-600">{studentStatsData.total}</div>
                                    <div className="text-sm text-gray-500">总签到天数</div>
                                </div>
                                <div style={styles.statCard}>
                                    <div className="text-2xl font-bold text-green-600">{studentStatsData.rate}%</div>
                                    <div className="text-sm text-gray-500">出勤率</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style={styles.card}>
                        <h3 className="font-bold mb-4 flex items-center gap-2">
                            <CalendarCheck size={20} className="text-indigo-500" />
                            近期记录
                        </h3>
                        <div>
                            {todaySigned && (
                                <div style={styles.historyItem} className="bg-green-50/50">
                                    <div className="flex items-center gap-3">
                                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                        <span className="font-medium text-green-700">今天</span>
                                    </div>
                                    <span className="font-mono text-sm text-green-600">12:30:45</span>
                                </div>
                            )}
                            {signHistory.map((record, index) => (
                                <div key={index} style={styles.historyItem}>
                                    <div className="flex items-center gap-3">
                                        <div className="w-2 h-2 rounded-full bg-gray-300"></div>
                                        <span>{record.date}</span>
                                    </div>
                                    <span className="font-mono text-sm text-gray-400">{record.time}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Teacher/President View
    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <div>
                    <h2 className="text-2xl font-bold">考勤管理</h2>
                    <p className="text-gray-500">管理学期与查看学生出勤</p>
                </div>
                {isTeacher && (
                    <button className="btn-primary" style={{ width: 'auto' }} onClick={handleSaveConfig}>
                        <Calendar size={18} />
                        保存设置
                    </button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div style={{ ...styles.card, gridColumn: 'span 1' }}>
                    <h3 className="font-bold mb-4">学期设置</h3>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-1 text-gray-500">开始日期</label>
                            <input
                                type="date"
                                className="input-field"
                                value={semesterStart}
                                onChange={(e) => isTeacher && setSemesterStart(e.target.value)}
                                disabled={!isTeacher}
                                style={{ backgroundColor: 'var(--bg-hover)', color: 'var(--text-primary)', borderColor: 'var(--border-color)' }}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1 text-gray-500">结束日期</label>
                            <input
                                type="date"
                                className="input-field"
                                value={semesterEnd}
                                onChange={(e) => isTeacher && setSemesterEnd(e.target.value)}
                                disabled={!isTeacher}
                                style={{ backgroundColor: 'var(--bg-hover)', color: 'var(--text-primary)', borderColor: 'var(--border-color)' }}
                            />
                        </div>
                    </div>
                </div>

                <div style={{ ...styles.card, gridColumn: 'span 2' }}>
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="font-bold">今日出勤概况</h3>
                        <span className="text-sm text-gray-500">{new Date().toLocaleDateString()}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="text-center p-4 rounded-lg bg-indigo-50">
                            <div className="text-2xl font-bold text-indigo-600">{teacherStats.signedToday}/{teacherStats.totalStudents}</div>
                            <div className="text-sm text-indigo-800">已签到</div>
                        </div>
                        <div className="text-center p-4 rounded-lg bg-red-50">
                            <div className="text-2xl font-bold text-red-600">{teacherStats.totalStudents - teacherStats.signedToday}</div>
                            <div className="text-sm text-red-800">未签到</div>
                        </div>
                        <div className="text-center p-4 rounded-lg bg-green-50">
                            <div className="text-2xl font-bold text-green-600">{teacherStats.totalDays > 0 ? Math.round(teacherStats.signedToday / teacherStats.totalStudents * 100) : 0}%</div>
                            <div className="text-sm text-green-800">今日出勤率</div>
                        </div>
                    </div>
                </div>
            </div>

            <div style={styles.card}>
                <h3 className="font-bold mb-4">学生考勤统计</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                                <th className="p-3 font-medium">姓名</th>
                                <th className="p-3 font-medium">总签到次数</th>
                                <th className="p-3 font-medium">出勤率</th>
                                <th className="p-3 font-medium">状态评级</th>
                            </tr>
                        </thead>
                        <tbody>
                            {teacherStats.students.map(student => (
                                <tr key={student.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td className="p-3 font-medium">{student.name}</td>
                                    <td className="p-3">{student.total}</td>
                                    <td className="p-3">
                                        <div className="flex items-center gap-2">
                                            <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full ${student.rate >= 90 ? 'bg-green-500' : student.rate >= 80 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                    style={{ width: `${student.rate}%` }}
                                                ></div>
                                            </div>
                                            <span className="text-sm">{student.rate}%</span>
                                        </div>
                                    </td>
                                    <td className="p-3">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${student.rate >= 90 ? 'bg-green-100 text-green-700' :
                                            student.rate >= 80 ? 'bg-yellow-100 text-yellow-700' :
                                                'bg-red-100 text-red-700'
                                            }`}>
                                            {student.rate >= 90 ? '优秀' : student.rate >= 80 ? '良好' : '需关注'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AttendanceView;
