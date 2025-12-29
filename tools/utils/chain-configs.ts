export interface ChainConfig {
  blocksPerDay: number;
  costPerBlock: number;
  costCollatorAssignment: number;
  alertThresholdDays: number;
}

// Chain-specific configurations
export const CHAIN_CONFIGS: Record<string, ChainConfig> = {
    tanssi: {
        blocksPerDay: 14400,
        costPerBlock: 0.03,
        costCollatorAssignment: 50,
        alertThresholdDays: 7,
    },
    dancelight: {
        blocksPerDay: 14400,
        costPerBlock: 0.03,
        costCollatorAssignment: 50,
        alertThresholdDays: 7,
    },
    flashbox: {
        blocksPerDay: 14400, // 1 block every 6 seconds
        costPerBlock: 0.03,
        costCollatorAssignment: 50,
        alertThresholdDays: 7,
    }
};
