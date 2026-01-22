import { ApiPromise, WsProvider } from '@polkadot/api';
import { Options } from 'yargs';

export type NetworkOptions = {
  network: Options & { type: 'string' };
  threshold: Options & { type: 'number' };
};

export type NETWORK_NAME =
  | 'flashbox'
  | 'dancelight'
  | 'tanssi';

export const NETWORK_WS_URLS: { [name in NETWORK_NAME]: string } = {
  dancelight: 'wss://services.tanssi-testnet.network/dancelight',
  flashbox: 'wss://fraa-flashbox-rpc.a.stagenet.tanssi.network',
  tanssi: 'wss://services.tanssi-mainnet.network/tanssi',
};

export const NETWORK_NAMES = Object.keys(NETWORK_WS_URLS) as NETWORK_NAME[];

export const NETWORK_YARGS_OPTIONS: NetworkOptions = {
  network: {
    type: 'string',
    choices: NETWORK_NAMES,
    description: 'Network to connect to',
    default: 'tanssi',
  },
  threshold: {
    type: 'number',
    description: 'Alert threshold in days (overrides chain config)',
  },
};

export const getApiFor = async (network: string) => {
  const wsProvider = new WsProvider(NETWORK_WS_URLS[network]);

  return await ApiPromise.create({
    noInitWarn: true,
    provider: wsProvider,
  });
};