import React, { useEffect, useRef, useState } from 'react';

/**
 * 开屏动画 / SplashScreen
 *
 * 效果：徽标在屏幕中央放大登场，停留片刻后沿最短路径飞向导航栏左侧，
 *       落地瞬间与导航栏里的真 logo 像素级重合，然后交接、淡出、卸载。
 *
 * 为什么能"无缝落地"：
 *   导航栏里的 logo 并不是整张图，而是一个 72×72 的方形裁剪框
 *   （.nav-logo-wrapper: overflow hidden + 左对齐，图高 72px），
 *   露出来的是图片左侧的圆形校徽。
 *   开屏这里用**完全相同**的裁剪方式，只是尺寸更大（SPLASH_SIZE），
 *   两者的裁剪比例一致，所以整段飞行只是"等比缩小 + 平移"，
 *   落点用 getBoundingClientRect 实测，不写死任何坐标。
 */

const SPLASH_SIZE = 200;   // 开屏徽标边长(px)
const HOLD_MS = 950;       // 登场后停留多久再起飞
const FLY_MS = 820;        // 飞行时长
const FADE_MS = 300;       // 交接淡出时长
const WAIT_NAV_MS = 1200;  // 最多等导航栏出现多久（访问 "/" 时会先重定向）

const SplashScreen = ({ onDone }) => {
  const logoRef = useRef(null);
  const [phase, setPhase] = useState('enter'); // enter -> fly -> leave

  // 用 ref 持有回调：这样 effect 只依赖空数组，动画严格只跑一次，
  // 不会因为父组件重渲染（回调标识变化）而重头再来。
  const onDoneRef = useRef(onDone);
  useEffect(() => { onDoneRef.current = onDone; }, [onDone]);

  useEffect(() => {
    const root = document.documentElement;
    const timers = [];
    let cancelled = false;

    const reduce =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const at = (ms, fn) => { timers.push(setTimeout(fn, ms)); };
    const finish = () => { const f = onDoneRef.current; if (f) f(); };

    // 开屏期间先藏住导航栏里的真 logo，避免同屏出现两个
    root.classList.add('splash-active');

    const land = () => {
      if (cancelled) return;
      setPhase('leave');
      root.classList.remove('splash-active');   // 真 logo 淡入，与开屏元素交叉
      at(FADE_MS, () => { if (!cancelled) finish(); });
    };

    const fly = () => {
      if (cancelled) return;
      setPhase('fly');

      const box = logoRef.current;
      const target = document.querySelector('.nav-logo-wrapper');

      // 找不到目标，或用户偏好减少动效 -> 不做飞行，直接淡出
      if (reduce || !box || !target) {
        at(360, land);
        return;
      }

      const from = box.getBoundingClientRect();
      const to = target.getBoundingClientRect();
      if (!from.width || !to.width) {
        at(360, land);
        return;
      }

      const scale = to.width / from.width;
      const dx = to.left - from.left;
      const dy = to.top - from.top;
      // 不用模板字符串拼 transform，避免与外层模板语法冲突
      const toTransform =
        'translate(' + dx + 'px, ' + dy + 'px) scale(' + scale + ')';

      let anim;
      try {
        anim = box.animate(
          [
            { transform: 'translate(0px, 0px) scale(1)' },
            { transform: toTransform },
          ],
          { duration: FLY_MS, easing: 'cubic-bezier(.22,.61,.36,1)', fill: 'forwards' }
        );
      } catch (e) {
        at(360, land);
        return;
      }
      anim.onfinish = land;
      anim.oncancel = land;
    };

    // 等两件事都就绪再开始计时：
    //   1. 导航栏渲染出来（访问 "/" 时会先 <Navigate> 到 /login）
    //   2. logo 图片加载完成（否则会看到空框，落点也就无从对齐）
    let waited = 0;
    const waitReady = () => {
      if (cancelled) return;
      const nav = document.querySelector('.nav-logo-wrapper');
      const img = document.querySelector('.splash-logo-img');
      const imgReady = !img || img.complete;
      if ((nav && imgReady) || waited >= WAIT_NAV_MS) {
        at(HOLD_MS, fly);
        return;
      }
      waited += 60;
      at(60, waitReady);
    };
    at(0, waitReady);

    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
      // 万一中途卸载（热更新等），别把导航栏的 logo 永久藏起来
      root.classList.remove('splash-active');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={'splash-overlay splash-' + phase}
      aria-hidden="true"
      data-splash="1"
    >
      <div className="splash-stage">
        {/* 外层只负责"登场"动画，内层只负责"飞行"，互不干扰 */}
        <div className="splash-logo-in">
          <div
            className="splash-logo-box"
            ref={logoRef}
            style={{ width: SPLASH_SIZE + 'px', height: SPLASH_SIZE + 'px' }}
          >
            <img
              src="/logo.png"
              alt=""
              className="splash-logo-img"
              style={{ height: SPLASH_SIZE + 'px' }}
            />
          </div>
        </div>

        <div className="splash-caption">
          <h1 className="gradient-text splash-title">AIGC 探索社</h1>
          <p className="splash-subtitle">厦门大学附属科技中学翔安校区</p>
        </div>
      </div>
    </div>
  );
};

export default SplashScreen;
