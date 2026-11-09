/**
 * dsh-vesta — 用 DSH 工具操作 VESTA（阶段 1）。
 *
 * 阶段 1 只做「文件级控制 + 命令行渲染 + 窗口管理」：
 *   - 用 VESTA 的命令行打开结构文件；
 *   - 用 `-open ... -export_img scale=N out.png` 直接渲染图片，不截屏、不看像素；
 *   - 列出 / 截取 / 关闭正在运行的 VESTA 窗口。
 * 这样既不需要视觉识别，也不会把屏幕内容塞进上下文。
 */

import { createVesta } from './lib/vesta.js';
import { registerVestaTools } from './lib/tools.js';

/** Cordis 插件行名称。 */
export const name = 'vesta';

/** 依赖工具注册表；缺少时插件保持不激活。 */
export const inject = ['tools'];

const PROMPT = [
  '## VESTA',
  'VESTA 通过 `vestaPath` 指定（插件配置或环境变量 `VESTA_EXE`）。`vesta_status` 查看路径、版本和正在运行的窗口；`vesta_open` 在桌面用 VESTA 打开结构文件；`vesta_export_image` 用命令行把结构文件或 `.vesta` 场景渲染成图片（渲染后用 read_image 检查）；`vesta_screenshot` 截取正在运行的 VESTA 窗口；`vesta_close` 关闭 VESTA。',
  '`.vesta` 场景文件是纯文本，记录了视角、显示范围、原子/键/多面体样式与光照；需要精确复现画面时，直接生成或修改场景文件再导出，不要靠界面点击。',
  'VESTA 是单实例程序：已有窗口时，新文件会在该窗口里新开标签页（不会替换已有文档），但会把焦点切到新标签。',
  '`vesta_export_image` 对 `.vesta` 场景支持覆盖参数：`view=[h,k,l]` 设定晶向视角（[0,0,1] 即沿 c 轴看）、`zoom` 模型大小、`boundary` 显示范围、`background` 背景色；不会改动原场景文件。',
].join('\n');

export function apply(ctx, rawConfig = {}) {
  const vesta = createVesta({ config: rawConfig ?? {}, logger: ctx.logger });
  registerVestaTools(ctx, vesta);

  ctx.inject(['systemPrompt'], (scoped) => {
    scoped.systemPrompt.section({
      name: 'vesta',
      order: 80,
      interpolate: false,
      text: PROMPT,
    });
  });

  ctx.effect(() => {
    const exe = vesta.exePath();
    const found = vesta.exists();
    if (typeof ctx.logger?.info === 'function') {
      ctx.logger.info(found ? `vesta: ready (${exe})` : `vesta: executable not found at ${exe}`);
    }
    return () => {};
  }, 'vesta: startup notice');

  return undefined;
}
