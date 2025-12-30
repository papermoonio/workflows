import axios from 'axios';
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
 * Includes trimming to prevent issues with hidden whitespace in CI/CD secrets
 */
export function loadSecrets(): SecretsConfig | null {
  try {
    // Try to read from environment variable (GitHub secret)
    const envSecret = process.env.TANSSI_APPCHAIN_FUNDING_MONITOR;
    
    if (envSecret) {
      process.stdout.write('Loading secrets from environment variable\n');
      // Trim the raw string to remove potential trailing newlines from GitHub UI
      const config = JSON.parse(envSecret.trim()) as SecretsConfig;
      
      // Sanitize the bot token inside the object
      if (config.telegramBotToken) {
        config.telegramBotToken = config.telegramBotToken.trim();
      }
      
      return config;
    }
    
    // Fallback to local .secrets.json file
    const secretsPath = join(process.cwd(), '.secrets.json');
    process.stdout.write('Loading secrets from local file\n');
    const fileContent = readFileSync(secretsPath, 'utf-8');
    return JSON.parse(fileContent) as SecretsConfig;
  } catch (error: any) {
    process.stderr.write(`Failed to load secrets: ${error.message}\n`);
    return null;
  }
}

/**
 * Send a message via Telegram Bot API using Axios
 * Replaces native fetch to improve reliability in GitHub Action environments
 */
export async function sendTelegramMessage(
  botToken: string,
  chatId: string,
  message: string
): Promise<boolean> {
  try {
    // Ensure the token is clean and format the URL
    const cleanToken = botToken.trim();
    const url = `https://api.telegram.org/bot${cleanToken}/sendMessage`;
    
    const response = await axios.post(url, {
      chat_id: chatId,
      text: message,
      parse_mode: 'Markdown',
    }, {
      timeout: 15000 // 15 second timeout for slow CI networks
    });

    if (response.status === 200) {
      return true;
    }
    
    return false;
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      // Detailed logging to identify if the issue is a 401 (token), 400 (chat_id), or 403 (blocked)
      const status = error.response?.status;
      const data = JSON.stringify(error.response?.data);
      process.stderr.write(`Telegram API Error [${status}]: ${data}\n`);
    } else {
      // Network level error (DNS, Connection Refused, etc.)
      process.stderr.write(`Telegram Network/Request Error: ${error.message}\n`);
    }
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
  // Ensure we compare numbers to numbers
  return secrets.teams.find(team => Number(team.para_id) === Number(paraId));
}
