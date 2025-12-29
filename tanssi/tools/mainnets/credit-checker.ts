import { u8aConcat } from '@polkadot/util';
import { blake2AsU8a, encodeAddress } from '@polkadot/util-crypto';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import { NETWORK_YARGS_OPTIONS, getApiFor } from '../utils/network';
import { CHAIN_CONFIGS } from '../utils/chain-configs';
import { loadSecrets, sendTelegramMessage, findTeamByParaId } from '../utils/notifications';

function parachainTank(paraId: number): Uint8Array {
  // Encode the prefix and para_id similar to Rust's using_encoded
  const prefix = new TextEncoder().encode('modlpy/serpayment');
  
  // Encode para_id as u32 little-endian
  const paraIdBytes = new Uint8Array(4);
  const view = new DataView(paraIdBytes.buffer);
  view.setUint32(0, paraId, true); // true for little-endian
  
  // Concatenate prefix and para_id bytes
  const combined = u8aConcat(prefix, paraIdBytes);
  
  // Hash with blake2_256
  const entropy = blake2AsU8a(combined, 256);
  
  // The entropy is already 32 bytes, which is what we need for an AccountId
  // In Substrate, TrailingZeroInput means we can read more zeros if needed
  // For AccountId32, we just need the 32 bytes from blake2_256
  return entropy;
}

yargs(hideBin(process.argv))
  .usage('Usage: $0')
  .version('1.0.0')
  .command(
    'checkCredits',
    'Check credits (free balance) for all registered container chains',
    (yargs) => {
      return yargs.options({
        ...NETWORK_YARGS_OPTIONS,
      });
    },
    async (argv) => {

        const networkName = argv.network || 'tanssi';
        const api = await getApiFor(networkName);

      // Get chain config based on network name or use default
      
      const config = CHAIN_CONFIGS[networkName];
      
      // Override threshold if provided via parameter
      const alertThreshold = argv.threshold ?? config.alertThresholdDays;
      
      // Load secrets for notifications
      const secrets = loadSecrets();
      const notificationsEnabled = secrets !== null;
      
      process.stdout.write(`Using config: ${config.blocksPerDay} blocks/day, ${config.costPerBlock} cost/block, ${config.costCollatorAssignment} collator assignment cost\n`);
      process.stdout.write(`Alert threshold: ${alertThreshold} days\n`);
      process.stdout.write(`Notifications: ${notificationsEnabled ? 'enabled' : 'disabled'}\n`);
      if (notificationsEnabled) {
        process.stdout.write(`Monitoring ${secrets.teams.length} team(s)\n`);
      }

      try {
        process.stdout.write('Fetching registered para IDs...\n');
        const registeredParaIds = await api.query.containerRegistrar.registeredParaIds();
        const paraIds = registeredParaIds.toJSON() as number[];

        if (paraIds.length === 0) {
          process.stdout.write('No registered container chains found.\n');
          return;
        }

        process.stdout.write(`Found ${paraIds.length} registered container chain(s)\n\n`);

        // Get the SS58 prefix for proper address formatting
        const ss58Format = api.registry.chainSS58?.[0] ?? 42;

        for (const paraId of paraIds) {
          // Derive the tank account for this para ID
          const tankAccountBytes = parachainTank(paraId);
          const tankAddress = encodeAddress(tankAccountBytes, ss58Format);

          // Query the free balance
          const accountInfo = await api.query.system.account(tankAccountBytes);
          const freeBalance = accountInfo.data.free.toString();

          // Query block production credits
          const blockProductionCredits = await api.query.servicesPayment.blockProductionCredits(paraId);
          const credits = blockProductionCredits.toString();

          // Format the balance with token decimals
          const decimals = api.registry.chainDecimals?.[0] ?? 12;
          const symbol = api.registry.chainTokens[0] || 'UNIT';
          const decimalsFactor = BigInt(10) ** BigInt(decimals);
          const formattedBalance = (BigInt(freeBalance) / decimalsFactor).toString();
          const remainder = (BigInt(freeBalance) % decimalsFactor).toString().padStart(decimals, '0');

          // Calculate remaining days
          // Days from credits: credits / BLOCKS_PER_DAY
          // Days from balance: balance / (daily cost from blocks + daily cost from collator assignment)
          // Collator assignment is charged every 6 hours (4 times per day)
          const creditsBigInt = BigInt(credits);
          const daysFromCredits = Number(creditsBigInt) / config.blocksPerDay;
          const balanceInTokens = Number(BigInt(freeBalance) / decimalsFactor);
          const dailyCost = config.costPerBlock * config.blocksPerDay + config.costCollatorAssignment * 4;
          const daysFromBalance = balanceInTokens / dailyCost;
          const totalRemainingDays = daysFromCredits + daysFromBalance;

          // Check if below threshold
          const isLowCredits = totalRemainingDays < alertThreshold;
          const alertIndicator = isLowCredits ? ' ⚠️  LOW CREDITS' : '';

          process.stdout.write(`Para ID ${paraId}:${alertIndicator}\n`);
          process.stdout.write(`  Address: ${tankAddress}\n`);
          process.stdout.write(`  Free Balance: ${formattedBalance}.${remainder.substring(0, 2)} ${symbol}\n`);
          process.stdout.write(`  Block Production Credits: ${credits}\n`);
          process.stdout.write(`  Remaining Days: ${totalRemainingDays.toFixed(2)}\n`);
          if (isLowCredits) {
            process.stdout.write(`  ⚠️  WARNING: Below threshold of ${alertThreshold} days!\n`);
            
            // Send Telegram notification if configured
            if (notificationsEnabled) {
              // Find specific team for this para_id
              const team = findTeamByParaId(secrets, paraId);
              
              // Find all teams with para_id=0 (broadcast recipients)
              const broadcastTeams = secrets.teams.filter(t => t.para_id === 0);
              
              let teamNotificationFailed = false;
              let teamNotFound = false;
              
              // Send to specific team with personalized message
              if (team) {
                const teamMessage = `⚠️ *Low Credits Alert*\n\n` +
                    `Your *${networkName}* chain with ID *${paraId}* is running low on credits.\n\n` +
                    `*Remaining Days:* ${totalRemainingDays.toFixed(2)}\n` +
                    `Visit [your dashboard](https://apps.tanssi.network/${networkName}/appchains/${paraId}) and top up credits soon!`;
                
                const sent = await sendTelegramMessage(secrets.telegramBotToken, team.chat_id, teamMessage);
                if (sent) {
                  process.stdout.write(`  📱 Telegram notification sent to ${team.name}\n`);
                } else {
                  process.stdout.write(`  ❌ Failed to send Telegram notification to ${team.name}\n`);
                  teamNotificationFailed = true;
                }
              } else {
                process.stdout.write(`  ⚠️  No team configuration found for Para ID ${paraId}\n`);
                teamNotFound = true;
              }
              
              // Send to broadcast teams with general message
              if (broadcastTeams.length > 0) {
                const teamNameInfo = team ? ` (*${team.name}*)` : '';
                let broadcastMessage = `⚠️ *Low Credits Alert*\n\n` +
                    `A *${networkName}* chain with ID *${paraId}*${teamNameInfo} is running low on credits.\n\n` +
                    `*Remaining Days:* ${totalRemainingDays.toFixed(2)}`;
                
                // Add warning if team not found or notification failed
                if (teamNotFound) {
                  broadcastMessage += `\n\n⚠️ _No team configuration found for this para ID._`;
                } else if (teamNotificationFailed && team) {
                  broadcastMessage += `\n\n⚠️ _Failed to notify ${team.name}._`;
                }
                
                for (const broadcastTeam of broadcastTeams) {
                  const sent = await sendTelegramMessage(secrets.telegramBotToken, broadcastTeam.chat_id, broadcastMessage);
                  if (sent) {
                    process.stdout.write(`  📱 Telegram notification sent to ${broadcastTeam.name}\n`);
                  } else {
                    process.stdout.write(`  ❌ Failed to send Telegram notification to ${broadcastTeam.name}\n`);
                  }
                }
              }
            }
          }
          process.stdout.write('\n');
        }

        process.stdout.write('Done ✅\n');
      } finally {
        await api.disconnect();
      }
    },
  )
  .demandCommand(1, 'You need to specify a command')
  .parse();