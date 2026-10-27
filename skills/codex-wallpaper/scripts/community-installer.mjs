import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';

const VERSION_ID = /^ver_[a-zA-Z0-9_-]{1,72}$/;
const THEME_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;
const MAX_PACKAGE = 32 * 1024 * 1024;

export function createCommunityInstaller({ catalog, cacheRoot, wrapperPath, fetchImpl = fetch, importImpl }) {
  let pending = false;
  let controller;
  let closed = false;

  async function install(id) {
    if (!VERSION_ID.test(id)) throw new Error('主题标识无效。');
    if (closed) throw new Error('图库已关闭，请重新打开。');
    if (pending) throw new Error('另一个主题正在安装，请稍后再试。');
    pending = true;
    let workspace;
    let timer;
    try {
      const info = await catalog.packageInfo(id);
      if (info.id !== id || !/^[0-9a-f]{64}$/.test(info.sha256)
          || !Number.isSafeInteger(info.bytes) || info.bytes < 1 || info.bytes > MAX_PACKAGE
          || info.downloadUrl !== `https://api.dreamskin.cc/v1/themes/${id}/download`) {
        throw new Error('社区主题的下载信息未通过校验。');
      }
      await fs.mkdir(cacheRoot, { recursive: true, mode: 0o700 });
      workspace = await fs.mkdtemp(path.join(cacheRoot, 'install-'));
      await fs.chmod(workspace, 0o700);
      const archive = path.join(workspace, 'theme.zip');
      controller = new AbortController();
      timer = setTimeout(() => controller.abort(), 180_000);
      const response = await fetchImpl(info.downloadUrl, { redirect: 'error', signal: controller.signal });
      if (!response.ok) throw new Error('主题下载失败，请稍后重试。');
      const length = response.headers.get('content-length');
      if (length !== null && Number(length) !== info.bytes) throw new Error('主题包字节数与社区记录不符。');
      const mime = (response.headers.get('content-type') ?? '').split(';')[0].trim();
      if (!['application/zip', 'application/octet-stream', 'application/x-zip-compressed'].includes(mime)) {
        throw new Error('下载内容不是主题 ZIP。');
      }
      if (!response.body) throw new Error('主题下载内容为空。');
      const chunks = [];
      let size = 0;
      for await (const chunk of response.body) {
        size += chunk.length;
        if (size > info.bytes || size > MAX_PACKAGE) {
          controller.abort();
          throw new Error('主题包超过允许的下载大小。');
        }
        chunks.push(Buffer.from(chunk));
      }
      clearTimeout(timer);
      const bytes = Buffer.concat(chunks);
      if (size !== info.bytes || crypto.createHash('sha256').update(bytes).digest('hex') !== info.sha256) {
        throw new Error('主题包完整性校验失败，已停止安装。');
      }
      if (closed) throw new Error('图库已关闭，安装已取消。');
      await fs.writeFile(archive, bytes, { flag: 'wx', mode: 0o600 });
      return importImpl ? await importImpl(archive, info) : await runImporter(archive, info);
    } catch (error) {
      if (controller?.signal.aborted) throw new Error(closed ? '图库已关闭，下载已取消。' : '主题下载超时，请稍后重试。');
      if (error instanceof Error && /^(主题|社区|下载|图库|另一个)/.test(error.message)) throw error;
      throw new Error('社区连接暂时失败，请稍后重试。');
    } finally {
      clearTimeout(timer);
      controller = undefined;
      if (workspace) await fs.rm(workspace, { recursive: true, force: true }).catch(() => {});
      pending = false;
    }
  }

  function runImporter(archive, info) {
    return new Promise((resolve, reject) => {
      const child = spawn(wrapperPath, ['import-zip', archive, '--expected-sha256', info.sha256, '--expected-bytes', String(info.bytes)], {
        stdio: ['ignore', 'pipe', 'pipe'], shell: false,
      });
      let output = '';
      let diagnostics = '';
      const timeout = setTimeout(() => child.kill('SIGTERM'), 60_000);
      child.stdout.setEncoding('utf8');
      child.stderr.setEncoding('utf8');
      child.stdout.on('data', chunk => { output = (output + chunk).slice(-65536); });
      child.stderr.on('data', chunk => { diagnostics = (diagnostics + chunk).slice(-65536); });
      child.once('error', () => { clearTimeout(timeout); reject(new Error('主题导入器暂时不可用。')); });
      child.once('close', code => {
        clearTimeout(timeout);
        if (code !== 0) {
          const known = diagnostics.match(/(?:SHA256 校验不匹配|ZIP 字节数不匹配|主题要求更高或不支持的引擎版本|主题样式未通过安全校验|主题图片未通过校验|ZIP 结构或内容未通过校验|ZIP 主题身份不明确或已存在；已拒绝覆盖)/);
          reject(new Error(known ? `主题安装失败：${known[0]}。` : '主题未通过本地引擎校验，未安装。'));
          return;
        }
        const id = output.match(/\[([A-Za-z0-9][A-Za-z0-9._-]{0,79})\]\s*$/)?.[1];
        if (!id || !THEME_ID.test(id)) { reject(new Error('主题已导入，但无法确认保存身份，请刷新本地列表。')); return; }
        resolve({ id, name: info.name, duplicate: output.startsWith('主题已存在') });
      });
    });
  }

  return { install, close() { closed = true; controller?.abort(); } };
}
