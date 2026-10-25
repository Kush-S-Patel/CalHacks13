import { Actor } from 'apify';
import { load } from 'cheerio';
import { createHash } from 'node:crypto';

await Actor.main(async () => {
  const input = await Actor.getInput();
  if (!Array.isArray(input?.urls) || input.urls.length !== 1) throw new Error('Exactly one official source URL is required.');
  const sourceUrl = new URL(input.urls[0]);
  if (sourceUrl.protocol !== 'https:' || sourceUrl.hostname !== 'www.govinfo.gov' || sourceUrl.port || sourceUrl.username || sourceUrl.password || !sourceUrl.pathname.startsWith('/content/pkg/')) {
    throw new Error('This Actor only retrieves HTTPS publication pages from www.govinfo.gov/content/pkg/.');
  }
  const previousHash = input.previous_hash ?? null;
  if (previousHash !== null && !/^[a-f0-9]{64}$/.test(previousHash)) throw new Error('previous_hash must be a SHA-256 hash.');
  const response = await fetch(sourceUrl, {
    redirect: 'error', signal: AbortSignal.timeout(30_000),
    headers: { 'User-Agent': 'SwarmCFO-Grant-Rule-Watcher/1.0', Accept: 'text/html' },
  });
  if (!response.ok) throw new Error(`Official publication returned HTTP ${response.status}.`);
  const chunks = []; let bytes = 0;
  for await (const chunk of response.body) {
    bytes += chunk.length;
    if (bytes > 2 * 1024 * 1024) throw new Error('Official publication exceeds the retrieval limit.');
    chunks.push(chunk);
  }
  const $ = load(Buffer.concat(chunks).toString('utf8'));
  const section = $('.SECTION').filter((_, element) => $(element).children('.SECTNO').text().includes('200.438')).first();
  if (!section.length) throw new Error('Section 200.438 was not found in the official publication.');
  const cleanText = section.text().replace(/\s+/g, ' ').trim();
  if (!cleanText.includes('Costs of entertainment') || cleanText.length < 100) throw new Error('The retrieved section is incomplete.');
  const contentHash = createHash('sha256').update(cleanText, 'utf8').digest('hex');
  await Actor.pushData({
    source_url: input.urls[0], title: '2 CFR § 200.438 — Entertainment and prizes',
    clean_text: cleanText, fetched_at: new Date().toISOString(), content_hash: contentHash,
    changed: previousHash !== contentHash, previous_hash: previousHash,
  });
});
