/**
 * 主题（浅色 / 深色）读写。
 *
 * 主题是挂在 <html data-theme="dark"> 上的全局状态，所有页面共用 index.css
 * 里那一套 CSS 变量。所以只要在应用启动时铺一次，/login、/dashboard、
 * /about 这些页面就自动保持同一个黑夜模式。
 */

const THEME_KEY = 'theme';

/** 读取"应该用什么主题"：优先用户上次的选择，否则跟随系统 */
export function resolveInitialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'dark') return true;
  if (saved === 'light') return false;
  return typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false;
}

/** 应用主题并记住用户的选择 */
export function applyTheme(dark) {
  const root = document.documentElement;
  if (dark) {
    root.setAttribute('data-theme', 'dark');
  } else {
    root.removeAttribute('data-theme');
  }
  localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light');
}
