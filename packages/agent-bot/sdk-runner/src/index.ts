import fs from 'node:fs';
import { query } from '@anthropic-ai/claude-agent-sdk';

type QueryFn = typeof query;

export interface RunnerRequest {
  prompt: string;
  user_id: string;
  session_id?: string | null;
  model?: string | null;
  max_turns?: number;
  system_prompt_text?: string | null;
  mcp_config_path: string;
}

export interface RunnerResponse {
  text: string | null;
  session_id: string | null;
  error: string | null;
}

interface McpServerConfig {
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

function expandEnv(value: string): string {
  return value.replace(/\$\{([^}]+)\}/g, (_, name: string) => process.env[name] ?? '');
}

function parseMcpServers(mcpConfigPath: string): Record<string, McpServerConfig> {
  const raw = fs.readFileSync(mcpConfigPath, 'utf-8');
  const parsed = JSON.parse(raw) as {
    mcpServers?: Record<string, { command: string; args?: string[]; env?: Record<string, string> }>;
  };

  const servers: Record<string, McpServerConfig> = {};
  for (const [name, server] of Object.entries(parsed.mcpServers ?? {})) {
    servers[name] = {
      command: server.command,
      args: server.args ?? [],
      env: Object.fromEntries(
        Object.entries(server.env ?? {}).map(([k, v]) => [k, expandEnv(v)]),
      ),
    };
  }
  return servers;
}

export async function runOnce(req: RunnerRequest, queryFn: QueryFn = query): Promise<RunnerResponse> {
  let sessionId: string | null = req.session_id ?? null;
  let text: string | null = null;

  const options: Record<string, unknown> = {
    cwd: '/app/bot/src',
    resume: req.session_id ?? undefined,
    maxTurns: req.max_turns ?? 10,
    mcpServers: parseMcpServers(req.mcp_config_path),
    permissionMode: 'bypassPermissions',
    allowDangerouslySkipPermissions: true,
    appendSystemPrompt: `The current user_id is: ${req.user_id}`,
  };

  if (req.model) {
    options.model = req.model;
  }

  if (req.system_prompt_text && req.system_prompt_text.trim()) {
    options.systemPrompt = {
      type: 'preset' as const,
      preset: 'claude_code' as const,
      append: req.system_prompt_text,
    };
  }

  try {
    for await (const message of queryFn({ prompt: req.prompt, options })) {
      if (message.type === 'system' && message.subtype === 'init' && 'session_id' in message) {
        sessionId = (message as { session_id: string }).session_id;
      }
      if (message.type === 'result') {
        const resultText = (message as { result?: string }).result;
        if (typeof resultText === 'string') {
          text = resultText;
        }
        if ((message as { is_error?: boolean }).is_error) {
          return {
            text: null,
            session_id: sessionId,
            error: resultText?.trim() || 'SDK returned an error result',
          };
        }
      }
    }

    return { text, session_id: sessionId, error: null };
  } catch (err) {
    return {
      text: null,
      session_id: sessionId,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export function normalizeOutput(
  success: { text: string | null; sessionId: string | null } | null,
  error: string | null,
): RunnerResponse {
  if (error) {
    return { text: null, session_id: null, error };
  }
  return {
    text: success?.text ?? null,
    session_id: success?.sessionId ?? null,
    error: null,
  };
}

async function readStdin(): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      data += chunk;
    });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

async function main(): Promise<void> {
  const input = await readStdin();
  const req = JSON.parse(input) as RunnerRequest;
  const out = await runOnce(req);
  process.stdout.write(`${JSON.stringify(out)}\n`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    const output: RunnerResponse = {
      text: null,
      session_id: null,
      error: err instanceof Error ? err.message : String(err),
    };
    process.stdout.write(`${JSON.stringify(output)}\n`);
    process.exit(1);
  });
}
