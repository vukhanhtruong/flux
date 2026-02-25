import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { normalizeOutput, runOnce, type RunnerRequest } from './index.js';

function makeRequest(mcpPath: string): RunnerRequest {
  return {
    prompt: 'hello',
    user_id: 'tg:123',
    mcp_config_path: mcpPath,
    max_turns: 1,
  };
}

function writeMcpConfig(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sdk-runner-'));
  const file = path.join(dir, 'mcp.json');
  fs.writeFileSync(
    file,
    JSON.stringify(
      {
        mcpServers: {
          flux: {
            command: 'python',
            args: ['-m', 'flux_mcp.server'],
            env: { DATABASE_URL: '${DATABASE_URL}' },
          },
        },
      },
      null,
      2,
    ),
    'utf-8',
  );
  return file;
}

describe('normalizeOutput', () => {
  it('maps success shape to runner response', () => {
    const out = normalizeOutput({ text: 'ok', sessionId: 'sess-1' }, null);
    assert.deepEqual(out, { text: 'ok', session_id: 'sess-1', error: null });
  });
});

describe('runOnce', () => {
  it('returns result text and session_id from query stream', async () => {
    const mcpPath = writeMcpConfig();
    async function* queryFn() {
      yield { type: 'system', subtype: 'init', session_id: 'sess-abc' };
      yield { type: 'result', result: 'done' };
    }

    const out = await runOnce(makeRequest(mcpPath), queryFn as never);
    assert.deepEqual(out, { text: 'done', session_id: 'sess-abc', error: null });
  });

  it('returns error when stream reports is_error', async () => {
    const mcpPath = writeMcpConfig();
    async function* queryFn() {
      yield { type: 'system', subtype: 'init', session_id: 'sess-abc' };
      yield { type: 'result', is_error: true, result: 'bad auth' };
    }

    const out = await runOnce(makeRequest(mcpPath), queryFn as never);
    assert.deepEqual(out, { text: null, session_id: 'sess-abc', error: 'bad auth' });
  });

  it('returns thrown error from sdk query', async () => {
    const mcpPath = writeMcpConfig();
    async function* queryFn() {
      throw new Error('boom');
      yield { type: 'result', result: 'never' };
    }

    const out = await runOnce(makeRequest(mcpPath), queryFn as never);
    assert.match(out.error ?? '', /boom/);
    assert.equal(out.text, null);
  });
});
