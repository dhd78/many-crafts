/**
 * 模型可见的 VESTA 工具。
 *
 * 五个工具覆盖阶段 1 的能力：查状态、打开文件、命令行渲染、截取窗口、关闭进程。
 * 参数与返回值都写成严格的 JSON Schema；渲染文本用中文，方便直接在会话里读。
 */

import path from 'node:path';

const WINDOW_ITEM_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    pid: { type: 'integer' },
    hwnd: { type: 'integer' },
    title: { type: 'string' },
    class: { type: 'string' },
    visible: { type: 'boolean' },
    width: { type: 'integer' },
    height: { type: 'integer' },
  },
  required: ['pid', 'hwnd', 'title', 'class', 'visible', 'width', 'height'],
};

const WINDOWS_SCHEMA = {
  type: 'array',
  items: WINDOW_ITEM_SCHEMA,
};

/** 会话工作目录；用于把相对路径解析成绝对路径。 */
function sessionCwd(exec) {
  const cwd = exec?.agent?.session?.header?.cwd;
  return typeof cwd === 'string' && cwd.length > 0 ? cwd : process.cwd();
}

/** 相对于会话目录解析路径。 */
function resolvePath(input, exec) {
  return path.isAbsolute(input) ? input : path.resolve(sessionCwd(exec), input);
}

/** 只展示有意义的窗口（可见且面积足够大），过滤 IME/提示类辅助窗口。 */
function meaningfulWindows(windows) {
  return windows.filter((win) => win.visible && win.width >= 120 && win.height >= 120);
}

/** 把窗口行压成模型友好的文本。 */
function describeWindows(windows) {
  if (windows.length === 0) return '当前没有正在运行的 VESTA 窗口。';
  const main = meaningfulWindows(windows);
  const rows = main.length > 0 ? main : windows;
  return rows
    .map((win) => `- PID ${win.pid}「${win.title || '(无标题)'}」${win.width}x${win.height}${win.visible ? '' : '（不可见）'}`)
    .join('\n');
}

/**
 * 注册全部 VESTA 工具。
 * @param {{ tools: { register: Function } }} ctx
 * @param {ReturnType<import('./vesta.js').createVesta>} vesta
 */
export function registerVestaTools(ctx, vesta) {
  ctx.tools.register({
    name: 'vesta_status',
    description:
      'Check the local VESTA installation and every VESTA window currently running: executable path, version, and per-window pid/title/size/visibility. No screenshots are taken. Call this first when unsure whether VESTA is installed or running.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {},
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          exe: { type: 'string' },
          exists: { type: 'boolean' },
          version: { type: 'string' },
          windows: WINDOWS_SCHEMA,
        },
        required: ['ok', 'exe', 'exists', 'windows'],
      },
      render: (_args, value) => {
        const lines = [
          value.exists ? `VESTA 已安装：${value.exe}` : `未找到 VESTA.exe：${value.exe}`,
          value.version === undefined ? '' : `版本：${value.version}`,
          describeWindows(value.windows),
        ].filter((line) => line !== '');
        return [{ type: 'text', text: lines.join('\n') }];
      },
    },
    async execute() {
      const info = await vesta.status();
      const result = {
        ok: info.exists,
        exe: info.exe,
        exists: info.exists,
        windows: info.windows,
      };
      if (typeof info.version === 'string') result.version = info.version;
      return result;
    },
  });

  ctx.tools.register({
    name: 'vesta_open',
    description:
      'Open one or more structure files (CIF, POSCAR/CONTCAR, .vesta scene, etc.) in the VESTA GUI on the desktop. VESTA must be installed locally. NOTE: VESTA is single-instance - when a window is already open, the new file is forwarded to that instance and opens as a new tab in the existing window (the active tab switches). Returns the launched pid, the resolved file list, whether a window was detected, and whether the request was forwarded to an existing window.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        paths: {
          type: 'array',
          minItems: 1,
          maxItems: 8,
          items: { type: 'string', description: 'Absolute path, or a path relative to the session working directory.' },
          description: 'Structure files to open, in order.',
        },
        waitMs: {
          type: 'integer',
          minimum: 0,
          maximum: 60000,
          description: 'How long to wait for a window to appear. Defaults to 6000 ms.',
        },
      },
      required: ['paths'],
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          pid: { type: 'integer' },
          files: { type: 'array', items: { type: 'string' } },
          detected: { type: 'boolean' },
          forwarded: { type: 'boolean' },
          windows: WINDOWS_SCHEMA,
        },
        required: ['ok', 'pid', 'files', 'detected', 'forwarded', 'windows'],
      },
      render: (_args, value) => {
        const lines = [
          value.forwarded
            ? `已把 ${value.files.length} 个文件转发给正在运行的 VESTA 窗口（PID ${value.pid} 的进程已退出）：`
            : `已启动 VESTA（PID ${value.pid}），打开 ${value.files.length} 个文件：`,
          ...value.files.map((file) => `- ${file}`),
          value.detected ? '检测到窗口：' : '进程已启动，但暂未检测到窗口（可能仍在加载，或当前桌面不可交互）。',
        ];
        if (value.detected) lines.push(describeWindows(value.windows));
        return [{ type: 'text', text: lines.join('\n') }];
      },
    },
    async execute(args, exec) {
      const paths = Array.isArray(args.paths) ? args.paths : [];
      const resolved = paths.map((file) => resolvePath(file, exec));
      const result = await vesta.open(resolved, { waitMs: args.waitMs });
      return {
        ok: true,
        pid: result.pid,
        files: result.files,
        detected: result.detected,
        forwarded: result.forwarded === true,
        windows: result.windows,
      };
    },
    timeoutMs: 90000,
  });

  ctx.tools.register({
    name: 'vesta_export_image',
    description:
      'Render a structure file or .vesta scene to a raster image through VESTA\'s command line (-open INPUT -export_img scale=N OUTPUT), with no GUI clicking and no screenshots. Returns the output path, byte size, and pixel dimensions; inspect it with read_image. For a .vesta scene you can also override the camera and scene: `view` [h,k,l] sets the viewing direction (crystal axes; identity-style [001] looks along c), `zoom` scales the model, `boundary` [aMin,aMax,bMin,bMax,cMin,cMax] sets the displayed range in fractional coordinates, `background` [r,g,b] sets the canvas color, and `saveSceneAs` keeps the modified scene. Overrides are applied to a temporary copy next to the input, so relative data paths keep working. NOTE: VESTA is single-instance - when a window is already open, this render runs inside it and opens the input as a new tab (the active tab switches); close VESTA first when the user\'s open session must stay untouched.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        input: {
          type: 'string',
          description: 'Structure file or .vesta scene to render. Absolute, or relative to the session working directory. Overrides require a .vesta scene.',
        },
        output: {
          type: 'string',
          description: 'Output image path. Defaults to the input path with a .png extension.',
        },
        scale: {
          type: 'integer',
          minimum: 1,
          maximum: 10,
          description: 'VESTA viewport scale multiplier (default 2). It multiplies the viewport, not a fixed pixel size.',
        },
        timeoutMs: {
          type: 'integer',
          minimum: 5000,
          maximum: 600000,
          description: 'Render timeout in milliseconds. Defaults to 120000.',
        },
        view: {
          type: 'array',
          minItems: 3,
          maxItems: 3,
          items: { type: 'number' },
          description: 'Viewing direction [h,k,l] in crystal coordinates, e.g. [0,0,1] looks down the c axis, [1,1,0] is a diagonal view.',
        },
        zoom: {
          type: 'number',
          minimum: 0.02,
          maximum: 20,
          description: 'Model scale stored in the scene (VESTA default is about 0.458; larger means a bigger model in the frame).',
        },
        boundary: {
          type: 'array',
          minItems: 6,
          maxItems: 6,
          items: { type: 'number' },
          description: 'Displayed range in fractional coordinates: [aMin,aMax,bMin,bMax,cMin,cMax]. [0,1,0,1,0,1] is one unit cell; [-1,1,-1,1,-1,1] is two cells per axis.',
        },
        background: {
          type: 'array',
          minItems: 3,
          maxItems: 3,
          items: { type: 'integer', minimum: 0, maximum: 255 },
          description: 'Canvas color [r,g,b], 0-255. Defaults to the scene value (usually white).',
        },
        saveSceneAs: {
          type: 'string',
          description: 'Optional path: write the modified .vesta scene here and keep it, instead of using a deleted temporary copy.',
        },
      },
      required: ['input'],
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          input: { type: 'string' },
          output: { type: 'string' },
          bytes: { type: 'integer' },
          width: { type: 'integer' },
          height: { type: 'integer' },
          scale: { type: 'integer' },
          applied: { type: 'array', items: { type: 'string' } },
          scene: { type: 'string' },
        },
        required: ['ok', 'input', 'output', 'bytes', 'width', 'height', 'scale', 'applied'],
      },
      render: (_args, value) => {
        const lines = [
          `已渲染：${value.output}`,
          `尺寸 ${value.width}x${value.height}，${Math.max(1, Math.round(value.bytes / 1024))} KB，scale=${value.scale}。`,
        ];
        if (value.applied.length > 0) lines.push(`场景覆盖：${value.applied.join('；')}`);
        if (typeof value.scene === 'string' && value.scene !== value.input) lines.push(`使用的场景：${value.scene}`);
        lines.push('用 read_image 查看这张图，确认视角、边界和样式后再决定是否重渲。');
        return [{ type: 'text', text: lines.join('\n') }];
      },
    },
    async execute(args, exec) {
      const overrides = {};
      if (args.view !== undefined) overrides.direction = args.view;
      if (args.zoom !== undefined) overrides.zoom = args.zoom;
      if (args.boundary !== undefined) overrides.boundary = args.boundary;
      if (args.background !== undefined) overrides.background = args.background;
      const hasOverrides = Object.keys(overrides).length > 0;
      if (hasOverrides && !/\.vesta$/i.test(args.input)) {
        throw new Error('view/zoom/boundary/background 只适用于 .vesta 场景文件；CIF 等结构文件请先在 VESTA 里另存为场景。');
      }

      const result = await vesta.renderScene({
        input: resolvePath(args.input, exec),
        output: args.output === undefined ? undefined : resolvePath(args.output, exec),
        scale: args.scale,
        timeoutMs: args.timeoutMs,
        signal: exec.signal,
        overrides,
        saveSceneAs: args.saveSceneAs === undefined ? undefined : resolvePath(args.saveSceneAs, exec),
      });
      const value = {
        ok: true,
        input: result.input,
        output: result.output,
        bytes: result.bytes,
        width: result.width,
        height: result.height,
        scale: result.scale,
        applied: result.applied,
      };
      if (typeof result.scene === 'string') value.scene = result.scene;
      return value;
    },
    timeoutMs: 660000,
  });

  ctx.tools.register({
    name: 'vesta_screenshot',
    description:
      'Capture one running VESTA window to a PNG file on disk (screen BitBlt of the window rectangle; OpenGL views are captured correctly). Returns the path and dimensions; inspect it with read_image. This is for checking live GUI state, not for rendering publication figures - use vesta_export_image for those.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        output: {
          type: 'string',
          description: 'PNG output path. Defaults to <session cwd>/vesta-shots/vesta-<timestamp>.png.',
        },
        pid: {
          type: 'integer',
          description: 'Optional VESTA process id from vesta_status. Defaults to the largest visible VESTA window.',
        },
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          output: { type: 'string' },
          bytes: { type: 'integer' },
          width: { type: 'integer' },
          height: { type: 'integer' },
          windowTitle: { type: 'string' },
          pid: { type: 'integer' },
        },
        required: ['ok', 'output', 'bytes', 'width', 'height', 'windowTitle', 'pid'],
      },
      render: (_args, value) => [{
        type: 'text',
        text: [
          `已截取 VESTA 窗口「${value.windowTitle || '(无标题)'}」：${value.output}`,
          `尺寸 ${value.width}x${value.height}，${Math.max(1, Math.round(value.bytes / 1024))} KB。`,
          '用 read_image 查看窗口内容。',
        ].join('\n'),
      }],
    },
    async execute(args, exec) {
      const defaultOutput = path.join(sessionCwd(exec), 'vesta-shots', `vesta-${Date.now()}.png`);
      const result = await vesta.screenshot({
        output: args.output === undefined ? defaultOutput : resolvePath(args.output, exec),
        pid: args.pid,
      });
      return {
        ok: true,
        output: result.output,
        bytes: result.bytes,
        width: result.width,
        height: result.height,
        windowTitle: result.windowTitle,
        pid: result.pid,
      };
    },
    timeoutMs: 60000,
  });

  ctx.tools.register({
    name: 'vesta_close',
    description:
      'Close every running VESTA window: sends WM_CLOSE first, waits, and only force-kills when force=true. Returns how many processes closed and how many remain. Unsaved changes may prompt inside VESTA; force=true discards them.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      properties: {
        force: {
          type: 'boolean',
          description: 'Force-kill remaining VESTA processes after the graceful close attempt. Defaults to false.',
        },
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          closed: { type: 'integer' },
          remaining: { type: 'integer' },
          forced: { type: 'boolean' },
        },
        required: ['ok', 'closed', 'remaining', 'forced'],
      },
      render: (_args, value) => [{
        type: 'text',
        text: value.remaining === 0
          ? `已关闭 ${value.closed} 个 VESTA 进程。`
          : `关闭 ${value.closed} 个，仍有 ${value.remaining} 个在运行${value.forced ? '（已尝试强制结束）' : '；如需强制结束请传 force=true'}。`,
      }],
    },
    async execute(args) {
      const result = await vesta.close({ force: args.force === true });
      return { ok: true, closed: result.closed, remaining: result.remaining, forced: result.forced };
    },
    timeoutMs: 60000,
  });
}
