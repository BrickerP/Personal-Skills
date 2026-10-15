import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const labels = {
  verified: '全部报告目标通过界面校验',
  'hidden-only': '主题身份与结构匹配；DOM 报告 hidden，无法据此确定原生窗口是否隐藏',
  'payload-mismatch': '主题 ID 或 revision 不匹配',
  'structure-failed': 'DOM 结构校验失败',
  'document-hidden': 'DOM 文档报告 hidden；仍有其他校验未通过',
  'native-window-unverified': '原生窗口状态无法验证',
  'renderer-failed': '界面校验未通过',
  'target-error': '目标无法读取',
  'invalid-report': '验证结果无效或不完整',
  'no-targets': '没有可验证的目标',
  'engine-error': '引擎退出状态与验证结果不一致',
};
const checkNames = ['documentVisible', 'fallbackWindowPass', 'nativeWindowPass',
  'payloadPass', 'structurePass', 'viewportPass', 'windowPass'];
const validId = (value) => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(value);
const validRevision = (value) => typeof value === 'string' && /^[a-f0-9]{20}$/.test(value);
const identity = (id, revision) => ({
  themeId: validId(id) ? id : null,
  revision: validRevision(revision) ? revision : null,
});

export function summarizeVerification(input, { exitCode, mode = 'verify', engineVersion, expectedThemeId } = {}) {
  const summary = { category: 'invalid-report', accepted: false, saved: identity(expectedThemeId, null), targets: [] };
  let report;
  try { report = JSON.parse(input); } catch { return summary; }
  if (!['once', 'verify'].includes(mode) || report?.mode !== mode || report.version !== engineVersion
    || !validId(expectedThemeId) || !Array.isArray(report.targets)) return summary;
  if (!report.targets.length) return { ...summary, category: 'no-targets' };

  let expectedRevision = null;
  let invalidExpected = false;
  summary.targets = report.targets.map((target) => {
    const r = target?.result;
    const targetSummary = { ...identity(r?.themeId, r?.revision), category: 'target-error', failedChecks: [],
      documentVisibility: ['visible', 'hidden'].includes(r?.documentVisibility) ? r.documentVisibility : 'unknown',
      nativeWindow: ['ready', 'not-ready', 'unsupported'].includes(r?.nativeWindow?.status) ? r.nativeWindow.status : 'unknown' };
    if (target?.error || !r || typeof r !== 'object') return targetSummary;
    const checks = r.checks;
    if (r.expectedThemeId !== expectedThemeId || !validRevision(r.expectedRevision)
      || (expectedRevision !== null && expectedRevision !== r.expectedRevision)) invalidExpected = true;
    if (validRevision(r.expectedRevision)) expectedRevision ??= r.expectedRevision;
    if (!checks || checkNames.some((key) => typeof checks[key] !== 'boolean') || typeof r.pass !== 'boolean') {
      return { ...targetSummary, category: 'invalid-report' };
    }
    targetSummary.failedChecks = checkNames.filter((key) => !checks[key]);
    const exactIdentity = validId(r.themeId) && validRevision(r.revision)
      && r.themeId === expectedThemeId && r.themeId === r.expectedThemeId && r.revision === r.expectedRevision;
    const mismatch = (validId(r.themeId) && r.themeId !== r.expectedThemeId)
      || (validRevision(r.revision) && r.revision !== r.expectedRevision);
    // Preserve the existing single-target exception, and still require a separate verify call after injection.
    const hiddenOnly = exitCode === 2 && report.targets.length === 1 && r.pass === false
      && r.installed === true && exactIdentity && r.documentVisibility === 'hidden'
      && r.version === engineVersion && r.nativeWindow?.status === 'unsupported'
      && r.stylePresent === true && r.businessClassPollution === 0
      && checks.documentVisible === false && checks.windowPass === false
      && checks.payloadPass === true && checks.structurePass === true && checks.viewportPass === true
      && checks.fallbackWindowPass === true && checks.nativeWindowPass === false;
    if (mismatch) targetSummary.category = 'payload-mismatch';
    else if (!exactIdentity) targetSummary.category = 'invalid-report';
    else if (hiddenOnly) targetSummary.category = 'hidden-only';
    else if (!checks.structurePass) targetSummary.category = 'structure-failed';
    else if (r.documentVisibility === 'hidden') targetSummary.category = 'document-hidden';
    else if (!['ready', 'unsupported'].includes(r.nativeWindow?.status)
      || (!checks.nativeWindowPass && !checks.fallbackWindowPass)) targetSummary.category = 'native-window-unverified';
    else if (r.pass && r.installed === true && r.version === engineVersion && checks.payloadPass
      && checks.structurePass && checks.viewportPass && checks.windowPass && checks.documentVisible
      && r.documentVisibility === 'visible'
      && ((r.nativeWindow.status === 'ready' && checks.nativeWindowPass)
        || (r.nativeWindow.status === 'unsupported' && checks.fallbackWindowPass))) {
      targetSummary.category = 'verified';
    } else targetSummary.category = 'renderer-failed';
    return targetSummary;
  });
  summary.saved = identity(expectedThemeId, invalidExpected ? null : expectedRevision);
  if (invalidExpected) return summary;
  const failed = summary.targets.find((target) => target.category !== 'verified');
  summary.category = failed?.category ?? (exitCode === 0 ? 'verified' : 'engine-error');
  summary.accepted = summary.category === 'verified' || (summary.category === 'hidden-only'
    && summary.targets.length === 1 && exitCode === 2);
  return summary;
}

export function formatSummary(summary) {
  const describe = (value) => `${value.themeId ?? '未取得'} / revision=${value.revision ?? '未取得'}`;
  const lines = [`验证结果：[${summary.category}] ${labels[summary.category]}`,
    `当前保存身份：${describe(summary.saved)}`];
  summary.targets.slice(0, 8).forEach((target, index) => {
    lines.push(`实时目标 ${index + 1}：${describe(target)}；[${target.category}] ${labels[target.category]}`
      + `；document=${target.documentVisibility}；native=${target.nativeWindow}`
      + (target.failedChecks.length ? `；未通过=${target.failedChecks.join(',')}` : ''));
  });
  if (summary.targets.length > 8) lines.push(`另有 ${summary.targets.length - 8} 个目标，均已计入总结果。`);
  return lines.join('\n');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [exitCode, mode, engineVersion, expectedThemeId] = process.argv.slice(2);
  const summary = summarizeVerification(readFileSync(0, 'utf8'), {
    exitCode: Number(exitCode), mode, engineVersion, expectedThemeId,
  });
  console.log(formatSummary(summary));
  process.exitCode = summary.accepted ? (summary.category === 'hidden-only' ? 3 : 0) : 1;
}
