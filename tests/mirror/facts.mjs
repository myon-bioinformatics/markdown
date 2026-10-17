// Independent readers for tests/test_mirror_js.py (no browser).
// Adapted from browser-test-kit scripts/mirror_facts.mjs: markdown-it (CommonMark) and
// marked (GFM) render, linkedom reads the HTML; string-width measures display width.
// stdin: {"markdown": [text, ...], "width": [text, ...]}  stdout: facts per reader.
import MarkdownIt from 'markdown-it';
import {marked} from 'marked';
import {parseHTML} from 'linkedom';
import stringWidth from 'string-width';

const input = JSON.parse(await new Promise((done) => {
  let data = '';
  process.stdin.on('data', (chunk) => (data += chunk)).on('end', () => done(data));
}));
const flat = (s) => s.replace(/\s+/g, ' ').trim();
function facts(html) {
  const {document} = parseHTML('<!doctype html><html><body>' + html + '</body></html>');
  return {
    headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map((h) => [Number(h.tagName[1]), flat(h.textContent)]),
    links: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')),
    images: [...document.querySelectorAll('img')].map((i) => [i.getAttribute('src'), i.getAttribute('alt') || '']),
    code: [...document.querySelectorAll('pre > code')].map((c) => [
      ((c.getAttribute('class') || '').match(/language-(\S+)/) || [, ''])[1], c.textContent.replace(/\n$/, '')]),
  };
}
const it = new MarkdownIt({html: true});
process.stdout.write(JSON.stringify({
  'markdown-it': input.markdown.map((text) => facts(it.render(text))),
  marked: input.markdown.map((text) => facts(marked.parse(text, {async: false}))),
  'string-width': input.width.map((text) => stringWidth(text)),
}));
