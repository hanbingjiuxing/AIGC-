import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

/**
 * 关于这个系统（/about）
 *
 * 这是一个独立页面（不带主界面的导航栏），左上角是返回按钮。
 * 主题沿用全局的 data-theme，所以和系统设置里的黑夜模式完全一致。
 * 整页尺寸自适应写在 index.css 的「关于这个系统」一节里。
 *
 * 三个板块：来源 → 实现与协议 → 出问题时怎么找人。
 */

// 联系方式（竖排，顺序即显示顺序）
const CONTACTS = [
  { label: 'QQ', value: '2944744365' },
  { label: '电话', value: '13806070132' },
  { label: '邮箱', value: '2944744365@qq.com' },
];

// 系统里实际用到的协议与数据格式
const PROTOCOLS = [
  ['HTTP / HTTPS', '浏览器与服务器之间的一切通信'],
  ['REST + JSON', '接口风格与数据格式'],
  ['JWT（Bearer 令牌）', '登录鉴权 —— 登录后每个请求都带着它'],
  ['SQL', 'SQLite 数据库的读写'],
  ['TCP/IP（局域网）', '一台机器当服务器，同网段设备直接访问'],
  ['Git（SSH）', '自动更新的首选通道'],
  ['GitHub REST API', '检查并下载 Release 更新包'],
  ['ZIP / DEFLATE / CRC32 / SHA-256', '更新包的打包、解压与完整性校验'],
];

const About = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // 从哪来回哪去：默认回「系统设置」那一栏
  const fromTab = (location.state && location.state.fromTab) || 'settings';

  const goBack = () => {
    navigate('/dashboard', { state: { tab: fromTab } });
  };

  return (
    <div className="about-page">
      <header className="about-header">
        <button type="button" className="about-back" onClick={goBack}>
          <ArrowLeft size={18} />
          <span>返回</span>
        </button>
      </header>

      <main className="about-body">
        <div className="about-hero">
          <div className="about-emblem">
            <img src="/logo.png" alt="社徽" />
          </div>
          <h1 className="about-title">关于这个系统</h1>
          <p className="about-subtitle">厦门大学附属科技中学翔安校区 AIGC 探索社</p>
        </div>

        <div className="about-content">
          {/* ---------------- 来源 ---------------- */}
          <section className="about-section">
            <h2 className="about-section-title">这套系统从哪来</h2>
            <p className="about-text">
              它由 <strong>27 届的学长</strong>受 <strong>纪丽丽老师</strong>委托，
              用 AI 一手做出来的。从第一行代码到你此刻看到的界面，全程都由 AI 辅助编写 ——
              前后用过 <strong>Claude、Gemini、DeepSeek、Mimo</strong> 等多种模型，
              哪家擅长什么就用哪家，反复试、反复改，最后拼成了一个真正能跑起来的系统。
            </p>
            <p className="about-text">
              它同时也是一个<strong>开源项目</strong>：代码全部公开，改得动、看得见，
              想自己部署一份也完全可以。
            </p>
          </section>

          {/* ---------------- 实现与协议 ---------------- */}
          <section className="about-section">
            <h2 className="about-section-title">它是怎么做出来的</h2>
            <p className="about-text">
              系统采用<strong>前后端分离</strong>的结构，三块各管一摊：
            </p>
            <ul className="about-list">
              <li>
                <strong>前端</strong>：React + Vite。你看到的每个页面、每次点击，
                都由它在浏览器里渲染出来。
              </li>
              <li>
                <strong>后端</strong>：Python + Flask。业务逻辑、权限判断、数据读写都在这里完成。
              </li>
              <li>
                <strong>数据库</strong>：SQLite。整个社团的数据就是一个文件，统一放在
                <code>data/</code> 目录下 —— 备份和迁移只需要拷这一个文件夹。
              </li>
            </ul>
            <p className="about-text">
              两者之间用 HTTP 传 JSON（REST 风格的接口）。登录成功后，服务器会签发一张
              <strong>JWT 令牌</strong>，之后每个请求都带着它，
              服务器据此判断你是谁、能做哪些事。
            </p>
            <p className="about-text">
              部署也不麻烦：老师在服务器上双击一次 <code>run_system.bat</code>，前后端一起启动，
              同一个局域网里的电脑、手机、平板打开浏览器就能用，不需要每台机器都装环境。
            </p>
            <p className="about-text">
              系统还内置了<strong>自动更新</strong>：优先用 Git 拉取最新代码，
              不行就回退到 GitHub Release 下载更新包。更新包是 ZIP，会校验 CRC32 与 SHA-256，
              写入前自动备份、失败自动回滚 —— 无论更新成功与否，
              数据库和同学们上传的作品都不会被动到。
            </p>

            <h3 className="about-subheading">用到的协议与格式</h3>
            <div className="about-table-wrap">
              <table className="about-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>用在哪</th>
                  </tr>
                </thead>
                <tbody>
                  {PROTOCOLS.map(([name, usage]) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td>{usage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ---------------- 联系 ---------------- */}
          <section className="about-section">
            <h2 className="about-section-title">遇到实在解决不了的 bug</h2>
            <p className="about-text">
              先重启一次 <code>run_system.bat</code> —— 九成的问题到这一步就没了。
            </p>
            <p className="about-text">
              要是还不行，可以通过下面的方式，联系
              <strong>古希腊掌管 AIGC 社信息系统的神</strong>：
            </p>

            {/* 左边三个联系方式竖排，右边头像；头像高度 = 左边那一列的高度（index.css） */}
            <div className="contact-row">
              <ul className="contact-list">
                {CONTACTS.map((c) => (
                  <li className="contact-item" key={c.label}>
                    <span className="contact-label">{c.label}</span>
                    <span className="contact-value">{c.value}</span>
                  </li>
                ))}
              </ul>
              <img
                className="contact-avatar"
                src="/api/assets/avatar"
                alt="古希腊掌管 AIGC 社信息系统的神"
                onError={(e) => {
                  // 保险箱/密钥不在、或后端没重启时退回社徽，避免裂图
                  if (!e.currentTarget.src.endsWith('/logo.png')) {
                    console.warn(
                      '[About] /api/assets/avatar 取不到，已退回社徽。请检查：' +
                      '① 后端是否用新代码重启过；② data/secrets/asset-vault.key 是否存在。'
                    );
                    e.currentTarget.src = '/logo.png';
                  }
                }}
              />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default About;
