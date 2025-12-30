import { readFileSync, existsSync } from 'fs';
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
  try {
    // Sanitize token to prevent malformed URL errors
    const cleanToken = botToken.trim();
    const url = `https://api.telegram.org/bot${cleanToken}/sendMessage`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: 'Markdown',
      }),
      // Native fetch doesn't have a default timeout; good to add one for CI/CD
      signal: AbortSignal.timeout(15000) 
    });

    if (!response.ok) {
      // Safely attempt to get error details
      const errorText = await response.text();
      console.error(`Telegram API error (${response.status}): ${errorText}`);
      return false;
    }

    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
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
