import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import dns from 'node:dns';

// Prefer IPv4 results first to reduce sporadic IPv6 connectivity issues on CI runners.
dns.setDefaultResultOrder('ipv4first');

export interface TeamConfig {
  name: string;
  para_id: number;
  chat_id: string;
}

export interface SecretsConfig {
  telegramBotToken: string;
  teams: TeamConfig[];
}

export function loadSecrets(): SecretsConfig | null {
  try {
    const envSecret = process.env.TANSSI_APPCHAIN_FUNDING_MONITOR;
    
    if (envSecret) {
      console.log('Loading secrets from environment variable');
      // .trim() is crucial for GitHub Secrets
      const config = JSON.parse(envSecret.trim()) as SecretsConfig;
      if (config.telegramBotToken) config.telegramBotToken = config.telegramBotToken.trim();
      return config;
    }
    
    const secretsPath = join(process.cwd(), '.secrets.json');
    if (!existsSync(secretsPath)) {
      console.error('Secrets source not found (Env or .secrets.json)');
      return null;
    }

    console.log('Loading secrets from local file');
    const fileContent = readFileSync(secretsPath, 'utf-8');
    return JSON.parse(fileContent) as SecretsConfig;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Failed to load secrets: ${message}`);
    return null;
  }
}

export async function sendTelegramMessage(
  botToken: string,
  chatId: string,
  message: string
): Promise<boolean> {
  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  try {
    // Sanitize token to prevent malformed URL errors
    const cleanToken = botToken.trim();
    const url = `https://api.telegram.org/bot${cleanToken}/sendMessage`;
    const { host } = new URL(url);

    const attempts = Number(process.env.TELEGRAM_FETCH_ATTEMPTS ?? 5);
    const timeoutMs = Number(process.env.TELEGRAM_FETCH_TIMEOUT_MS ?? 25000);
    const debug = process.env.TELEGRAM_FETCH_DEBUG === '1';

    for (let attempt = 1; attempt <= attempts; attempt++) {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chat_id: chatId,
            text: message,
            parse_mode: 'Markdown',
          }),
          // Native fetch doesn't have a default timeout; good to add one for CI/CD
          signal: AbortSignal.timeout(timeoutMs),
        });

        if (!response.ok) {
          // Safely attempt to get error details
          const errorText = await response.text();
          console.error(`Telegram API error (${response.status}): ${errorText}`);
          return false;
        }

        return true;
      } catch (error) {
        const err = error as unknown as { message?: string; name?: string; cause?: unknown };
        const message = err?.message ?? String(error);
        const cause = err?.cause as
          | undefined
          | {
              name?: string;
              message?: string;
              code?: string;
              errno?: string | number;
              syscall?: string;
              address?: string;
              port?: number;
            };

        const isFinalAttempt = attempt >= attempts;
        if (debug || isFinalAttempt) {
          const log = isFinalAttempt ? console.error : console.warn;
          log(
            `Failed to send Telegram message (attempt ${attempt}/${attempts}) to host=${host}, timeoutMs=${timeoutMs}: ${message}`
          );
          if (cause) {
            log('Telegram fetch error cause:', {
              name: cause.name,
              message: cause.message,
              code: cause.code,
              errno: cause.errno,
              syscall: cause.syscall,
              address: cause.address,
              port: cause.port,
            });
          }
        }

        if (attempt < attempts) {
          const baseDelayMs = 400;
          const maxDelayMs = 4000;
          const backoffMs = Math.min(maxDelayMs, baseDelayMs * 2 ** (attempt - 1));
          const jitterMs = Math.floor(Math.random() * 200);
          await sleep(backoffMs + jitterMs);
          continue;
        }

        return false;
      }
    }

    return false;
  } catch (error) {
    const err = error as unknown as { message?: string; name?: string; cause?: unknown };
    const message = err?.message ?? String(error);
    console.error(`Failed to send Telegram message: ${message}`);
    return false;
  }
}

export function findTeamByParaId(
  secrets: SecretsConfig,
  paraId: number | string
): TeamConfig | undefined {
  // Use Number() to ensure comparison works even if paraId is passed as a string from CLI
  return secrets.teams.find(team => Number(team.para_id) === Number(paraId));
}
