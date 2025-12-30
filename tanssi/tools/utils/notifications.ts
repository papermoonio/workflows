import { readFileSync } from 'fs';
import { join } from 'path';

export interface TeamConfig {
  name: string;
  para_id: number;
  chat_id: string;
}

export interface SecretsConfig {
  telegramBotToken: string;
  teams: TeamConfig[];
}

/**
 * Load secrets from GitHub environment variable or local file
 */
export function loadSecrets(): SecretsConfig | null {
  try {
    // Try to read from environment variable (GitHub secret)
    const envSecret = process.env.TANSSI_APPCHAIN_FUNDING_MONITOR;
    
    if (envSecret) {
      process.stdout.write('Loading secrets from environment variable\n');
      return JSON.parse(envSecret) as SecretsConfig;
    }
    
    // Fallback to local .secrets.json file
    const secretsPath = join(process.cwd(), '.secrets.json');
    process.stdout.write('Loading secrets from local file\n');
    const fileContent = readFileSync(secretsPath, 'utf-8');
    return JSON.parse(fileContent) as SecretsConfig;
  } catch (error) {
    process.stderr.write(`Failed to load secrets: ${error.message}\n`);
    return null;
  }
}

/**
 * Send a message via Telegram Bot API
 */
export async function sendTelegramMessage(
  botToken: string,
  chatId: string,
  message: string
): Promise<boolean> {
  try {
    const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: 'Markdown',
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      process.stderr.write(`Telegram API error: ${JSON.stringify(errorData)}\n`);
      return false;
    }

    return true;
  } catch (error) {
    process.stderr.write(`Failed to send Telegram message: ${error.message}\n`);
    return false;
  }
}

/**
 * Find team configuration by para ID
 */
export function findTeamByParaId(
  secrets: SecretsConfig,
  paraId: number
): TeamConfig | undefined {
  return secrets.teams.find(team => team.para_id === paraId);
}
